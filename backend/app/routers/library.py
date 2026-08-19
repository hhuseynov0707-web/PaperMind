"""İstifadəçinin kitabxanası — «research memory»nin ilk qatı.

Üç vəziyyət var və hamısı BİR sətirdə saxlanılır (bax: `models.SavedPaper`):

    saved    — oxu siyahısında
    starred  — ulduzlanmış
    read_at  — oxunub, nə vaxt oxunduğu ilə birlikdə

Yazma yolu BİRDİR: `PUT /{paper_id}`. «Ulduzla», «saxla», «oxundu işarələ»
üçün ayrıca endpoint qurmadıq, çünki onlar eyni sətri dəyişir — ayrı olsaydı,
iki düymə eyni anda basılanda hansının qazandığı endpointlərin sırasından
asılı olardı və limit yoxlaması üç yerdə təkrarlanardı.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import auth, models, plans
from ..database import get_db
from ..schemas import LibraryStateOut, PaperOut, PaperStateIn, PaperStateOut, SavedPaperOut

router = APIRouter(prefix="/api/library", tags=["library"])


def resolve_state(
    *, cur_saved: bool, cur_starred: bool, cur_read: bool, req: PaperStateIn
) -> tuple[bool, bool, bool]:
    """Yamadan sonrakı hədəf vəziyyəti hesablayır — bazadan asılı deyil.

    Ayrıca funksiyadır ki, qaydalar BİR yerdə olsun və bazaya toxunmadan
    yoxlanıla bilsin. Router-in içində qalsaydı, «ulduz saxlamanı da qoşur»
    qaydasını test etmək üçün tam istifadəçi + məqalə + sessiya qurmaq
    lazım gələrdi və qayda praktikada heç yoxlanmazdı.

    `None` «dəymə» deməkdir — yalnız göndərilən sahə dəyişir.
    """
    saved = cur_saved if req.saved is None else req.saved
    starred = cur_starred if req.starred is None else req.starred
    read = cur_read if req.read is None else req.read

    # Bu iki qayda bir-biri ilə toqquşa bilir, ona görə NİYYƏTƏ görə sıralanır:
    # şərt daşınan dəyərə yox, sorğunun AÇIQ göndərdiyi sahəyə baxır.
    #
    # Sadəcə `if starred: saved = True` yazılsaydı, ulduzlu məqaləni
    # kitabxanadan çıxarmaq mümkün olmazdı: `saved=False` gəlir, ulduz köhnə
    # sətirdən daşınır, qayda saxlamanı geri qaytarır və düymə heç nə etmir.
    if req.starred is True:
        saved = True            # ulduzlamaq məqaləni siyahıya da salır
    elif req.saved is False:
        starred = False         # siyahıdan çıxarmaq ulduzu da götürür
    elif starred and not saved:
        saved = True            # uyğunsuz köhnə sətri sakitcə düzəldir

    return saved, starred, read


@router.get("", response_model=list[SavedPaperOut])
def list_saved(
    view: str = Query("saved", pattern="^(saved|starred|read)$"),
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_user),
):
    """Kitabxananın bir görünüşü.

    Üç ayrı endpoint əvəzinə bir parametr: sorğu məntiqi eynidir, yalnız
    filtr və sıralama dəyişir. `read` görünüşü oxunma vaxtına görə düzülür,
    digərləri əlavə olunma vaxtına görə — «tarixçə» sıralanmasa tarixçə deyil.
    """
    q = db.query(models.SavedPaper).filter(models.SavedPaper.user_id == user.id)

    if view == "starred":
        q = q.filter(models.SavedPaper.starred.is_(True))
        q = q.order_by(models.SavedPaper.created_at.desc())
    elif view == "read":
        q = q.filter(models.SavedPaper.read_at.isnot(None))
        q = q.order_by(models.SavedPaper.read_at.desc())
    else:
        q = q.filter(models.SavedPaper.saved.is_(True))
        q = q.order_by(models.SavedPaper.created_at.desc())

    return [
        SavedPaperOut(
            paper=_paper_out(r.paper),
            note=r.note,
            created_at=r.created_at,
            starred=r.starred,
            read_at=r.read_at,
        )
        for r in q.all()
        if r.paper is not None
    ]


@router.get("/state", response_model=LibraryStateOut)
def library_state(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_user),
):
    """Yalnız ID-lər — interfeys hər kartın vəziyyətini bundan bilir.

    Axtarış nəticəsindəki 20 kart üçün 20 sorğu atmaq əvəzinə bir sorğu.
    Tam məqalə obyektləri qaytarılmır, çünki onlar artıq axtarış cavabındadır.
    """
    rows = (
        db.query(
            models.SavedPaper.paper_id,
            models.SavedPaper.saved,
            models.SavedPaper.starred,
            models.SavedPaper.read_at,
        )
        .filter(models.SavedPaper.user_id == user.id)
        .all()
    )
    return LibraryStateOut(
        saved=[r.paper_id for r in rows if r.saved],
        starred=[r.paper_id for r in rows if r.starred],
        read=[r.paper_id for r in rows if r.read_at is not None],
    )


@router.put("/{paper_id}", response_model=PaperStateOut)
def set_state(
    paper_id: int,
    req: PaperStateIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_capability(plans.SAVE)),
):
    """Vəziyyət yaması — göndərilməyən sahə toxunulmaz qalır."""
    if db.get(models.Paper, paper_id) is None:
        raise HTTPException(status_code=404, detail="Məqalə tapılmadı.")

    row = (
        db.query(models.SavedPaper)
        .filter(
            models.SavedPaper.user_id == user.id,
            models.SavedPaper.paper_id == paper_id,
        )
        .first()
    )

    was_saved = bool(row and row.saved)
    saved, starred, read = resolve_state(
        cur_saved=was_saved,
        cur_starred=bool(row and row.starred),
        cur_read=bool(row and row.read_at),
        req=req,
    )

    # Limit YALNIZ yeni saxlamada yoxlanılır. Mövcud məqaləni oxundu işarələmək
    # kitabxananı böyütmür, ona görə dolu kitabxanada da işləməlidir.
    if saved and not was_saved:
        limit = plans.get_plan(user.plan).library_limit
        used = (
            db.query(models.SavedPaper)
            .filter(
                models.SavedPaper.user_id == user.id,
                models.SavedPaper.saved.is_(True),
            )
            .count()
        )
        if used >= limit:
            # 402 + strukturlaşdırılmış detal: interfeys bunu ümumi xətadan
            # ayırıb kontekstli yüksəltmə təklifi göstərir (§20).
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "library_full",
                    "limit": limit,
                    "plan": user.plan,
                    "message": f"Kitabxana doldu ({limit} məqalə).",
                },
            )

    # Heç bir vəziyyət qalmayıbsa sətir də qalmamalıdır.
    if not (saved or starred or read):
        if row is not None:
            db.delete(row)
            db.commit()
        return PaperStateOut(paper_id=paper_id)

    if row is None:
        row = models.SavedPaper(user_id=user.id, paper_id=paper_id)
        db.add(row)

    row.saved = saved
    row.starred = starred
    if read:
        # Mövcud vaxt SAXLANILIR: tarixçə «nə vaxt oxudum» sualına cavab verir,
        # təkrar işarələmə onu yuxarı atıb sıranı pozmamalıdır.
        if row.read_at is None:
            row.read_at = datetime.now(timezone.utc)
    else:
        row.read_at = None
    if req.note is not None:
        row.note = req.note

    db.commit()
    db.refresh(row)
    return PaperStateOut(
        paper_id=paper_id,
        saved=row.saved,
        starred=row.starred,
        read=row.read_at is not None,
        read_at=row.read_at,
    )


@router.delete("/{paper_id}", status_code=204)
def remove_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_user),
):
    """Tam unutma — hər üç vəziyyət birdən silinir."""
    # Filtr HƏMİŞƏ user_id daxildir — başqasının sətrini silmək mümkün olmasın.
    db.query(models.SavedPaper).filter(
        models.SavedPaper.user_id == user.id,
        models.SavedPaper.paper_id == paper_id,
    ).delete()
    db.commit()


def _paper_out(paper: models.Paper) -> PaperOut:
    return PaperOut(
        id=paper.id,
        arxiv_id=paper.arxiv_id,
        doi=paper.doi,
        title=paper.title,
        abstract=paper.abstract,
        primary_category=paper.primary_category,
        published_at=paper.published_at,
        pdf_url=paper.pdf_url,
        language=paper.language,
        authors=[a.name for a in paper.authors],
        categories=[c.code for c in paper.categories],
        field_keys=list(paper.field_keys or []),
        sources=sorted({s.source for s in paper.sources}),
    )
