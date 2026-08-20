"""Şəxsi PDF sənədləri — yükləmə, siyahı, silmə və sənəd üzrə sual.

Təhlükəsizlik qaydası: **hər sorğu `user_id` ilə filtrlənir.** Bir yerdə
unudulsa, istifadəçi başqasının şəxsi sənədini oxuyar. Ona görə sənəd həmişə
`_owned()` vasitəsilə alınır, birbaşa `db.get()` ilə yox.

RAG qatı YENİDƏN YAZILMIR: `select_evidence`, `label_blocks`,
`validate_citations` və `ask_llm` olduğu kimi işlədilir. Onlar bloklardan
yalnız `.title` və `.content` gözləyir, ona görə sənəd parçaları üçün eyni
formada kiçik obyektlər verilir. İkinci, paralel RAG axını saxlamaq eyni
səhvi iki dəfə etmək deməkdir.
"""

import time
from dataclasses import dataclass

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import auth, limits, models, pdf, plans
from ..config import settings
from ..database import SessionLocal, get_db
from ..providers import get_embedder
from ..rag.chunker import embedding_signature
from ..rag.evidence import label_blocks, select_evidence, validate_citations
from ..rag.llm import ask_llm
from ..rag.translator import detect_lang
from ..schemas import DocumentAskRequest, DocumentAskResponse, DocumentOut

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Embedding partiyası: 300 səhifəlik sənədin bütün parçalarını bir dəfəyə
# vermək yaddaşı partladır. Backend konteynerinin limiti 2 GB-dır.
EMBED_BATCH = 32


@dataclass
class _Doc:
    """`ask_llm` üçün `.title` verən kiçik obyekt.

    Səhifə nömrəsi məhz başlığa yazılır ki, model hansı səhifədən danışdığını
    görsün və cavabda ona istinad edə bilsin.
    """

    title: str


@dataclass
class _Chunk:
    content: str


def _owned(db: Session, user: models.User, doc_id: int) -> models.Document:
    doc = db.scalar(
        select(models.Document).where(
            models.Document.id == doc_id,
            models.Document.user_id == user.id,      # izolyasiya BURADADIR
        )
    )
    if doc is None:
        # 404, 403 yox: başqasının sənədinin MÖVCUDLUĞUNU da açıqlamırıq.
        raise HTTPException(status_code=404, detail="Sənəd tapılmadı.")
    return doc


def _out(doc: models.Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        filename=doc.filename,
        title=doc.title,
        pages=doc.pages,
        chunk_count=doc.chunk_count,
        status=doc.status,
        error=doc.error,
        created_at=doc.created_at,
    )


# --------------------------------------------------------------------- emal

def _process(document_id: int, chunks: list[tuple[int, str]]) -> None:
    """Fonda: parçaları embed edib yazır.

    Öz sessiyasını açır — sorğunun sessiyası cavab göndəriləndən sonra bağlanır.

    Xəta baş verərsə sənəd `failed` olur və səbəb saxlanılır. Səssiz uğursuzluq
    istifadəçini «hazırlanır» vəziyyətində əbədi saxlayardı, o isə nə gözləməli,
    nə də yenidən cəhd etməli olduğunu bilməzdi.
    """
    db = SessionLocal()
    try:
        doc = db.get(models.Document, document_id)
        if doc is None:
            return
        embedder = get_embedder()
        signature = embedding_signature(settings.embedding_model)

        written = 0
        for start in range(0, len(chunks), EMBED_BATCH):
            batch = chunks[start:start + EMBED_BATCH]
            vectors = embedder.embed([text for _, text in batch])
            for offset, ((page, text), vector) in enumerate(zip(batch, vectors)):
                db.add(
                    models.DocumentChunk(
                        document_id=document_id,
                        page=page,
                        chunk_index=start + offset,
                        content=text,
                        embedding=vector,
                        embedding_model=signature,
                    )
                )
            written += len(batch)
            db.commit()

        doc.chunk_count = written
        doc.status = "ready"
        doc.error = None
        db.commit()
    except Exception as exc:
        db.rollback()
        doc = db.get(models.Document, document_id)
        if doc is not None:
            doc.status = "failed"
            doc.error = str(exc)[:400]
            db.commit()
    finally:
        db.close()


# ----------------------------------------------------------------- endpoint

async def _read_capped(file: UploadFile) -> bytes:
    """Faylı hissə-hissə oxuyur və limiti keçən kimi DAYANDIRIR.

    Əvvəl `await file.read()` bütün faylı yaddaşa alırdı, 20 MB limiti isə
    ondan SONRA `pdf.parse()` içində yoxlanılırdı. Yəni 2 GB-lıq yükləmə
    limitə heç çatmadan konteynerin yaddaşını tükədirdi — hesabı olan bir
    nəfər serveri yıxa bilərdi.

    İndi limit oxumanın İÇİNDƏDİR: 20 MB-ı keçən bayt heç vaxt yaddaşa
    yığılmır. 413 qaytarılır (422 yox) — semantik olaraq doğrudur və
    proxy səviyyəsində də eyni koddur.
    """
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(64 * 1024):
        total += len(chunk)
        if total > pdf.MAX_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Fayl çox böyükdür. Limit: {pdf.MAX_BYTES // 1024 // 1024} MB.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("", response_model=DocumentOut, status_code=201)
async def upload(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_capability(plans.UPLOAD_PDF)),
):
    limits.enforce("upload", user_id=user.id)

    data = await _read_capped(file)
    if not data:
        raise HTTPException(status_code=422, detail="Fayl boşdur.")

    try:
        parsed = pdf.parse(data, file.filename or "sənəd.pdf")
    except pdf.PdfError as exc:
        # 422 və istifadəçiyə ANLAŞILAN səbəb: «skan edilmiş şəkildir»,
        # «parolla qorunub», «çox böyükdür». Ümumi «xəta baş verdi» faydasızdır.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    existing = db.scalar(
        select(models.Document).where(
            models.Document.user_id == user.id,
            models.Document.digest == parsed["digest"],
        )
    )
    if existing is not None:
        # Eyni fayl təkrar yüklənəndə dublikat yaratmırıq.
        return _out(existing)

    doc = models.Document(
        user_id=user.id,
        filename=(file.filename or "sənəd.pdf")[:300],
        title=parsed["title"][:300],
        digest=parsed["digest"],
        pages=parsed["pages"],
        chars=parsed["chars"],
        status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Embedding uzun çəkir və cavabı gözlətməməlidir.
    background.add_task(_process, doc.id, parsed["chunks"])
    return _out(doc)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_user),
):
    rows = db.scalars(
        select(models.Document)
        .where(models.Document.user_id == user.id)
        .order_by(models.Document.created_at.desc())
    ).all()
    return [_out(d) for d in rows]


@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_user),
):
    doc = _owned(db, user, doc_id)
    db.delete(doc)          # parçalar cascade ilə silinir
    db.commit()


@router.post("/{doc_id}/ask", response_model=DocumentAskResponse)
def ask_document(
    doc_id: int,
    req: DocumentAskRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_capability(plans.UPLOAD_PDF)),
):
    """Bir sənəd üzrə sual — istinadlar SƏHİFƏ nömrəsi ilə."""
    t0 = time.perf_counter()
    doc = _owned(db, user, doc_id)
    if doc.status != "ready":
        raise HTTPException(
            status_code=409,
            detail=(
                "Sənəd hələ hazır deyil."
                if doc.status == "processing"
                else f"Sənəd emal olunmadı: {doc.error or 'naməlum səbəb'}"
            ),
        )

    vector = get_embedder().embed([req.question])[0]
    # Axtarış YALNIZ bu sənədin içindədir. HNSW indeksi yoxdur və lazım deyil —
    # bir sənəddə bir neçə yüz parça olur, ardıcıl oxuma daha sürətlidir.
    rows = db.execute(
        select(
            models.DocumentChunk,
            models.DocumentChunk.embedding.cosine_distance(vector).label("dist"),
        )
        .where(models.DocumentChunk.document_id == doc.id)
        .order_by("dist")
        .limit(req.top_k)
    ).all()

    if not rows:
        raise HTTPException(status_code=404, detail="Sənəddə mətn tapılmadı.")

    blocks = [
        {
            "paper": _Doc(title=f"{doc.title or doc.filename} — səh. {chunk.page}"),
            "chunk": _Chunk(content=chunk.content),
            "score": round(1.0 - float(dist), 4),
            "page": chunk.page,
        }
        for chunk, dist in rows
    ]

    blocks, ev = select_evidence(blocks, max_blocks=req.top_k)
    lang = detect_lang(req.question)

    try:
        answer = ask_llm(
            req.question,
            blocks,
            lang=lang,
            history=[t.model_dump() for t in req.history],
            weak=ev["weak"],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Groq xətası: {exc}") from exc

    answer, cites = validate_citations(answer, set(label_blocks(blocks)))

    # Kredit yalnız cavab alındıqdan sonra yazılır — Groq xətası istifadəçinin
    # kreditini yandırmamalıdır (`/api/ask` ilə eyni qayda).
    auth.charge(db, user, plans.ASK, {"kind": "document", "doc": doc.id})

    return DocumentAskResponse(
        answer=answer,
        document={"id": doc.id, "title": doc.title, "filename": doc.filename},
        sources=[
            {
                "page": b["page"],
                "score": b["score"],
                "excerpt": b["chunk"].content[:280],
            }
            for b in blocks
        ],
        grounding={
            "evidence_used": ev["kept"],
            "evidence_dropped": ev["dropped"],
            "top_score": ev["top_score"],
            "weak": ev["weak"],
            "citations_valid": cites["valid"],
            "citations_removed": cites["invented"],
            "coverage": cites["coverage"],
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
        credits_left=auth.credits_left(user),
    )
