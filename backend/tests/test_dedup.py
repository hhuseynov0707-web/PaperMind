"""Deduplikasiyanın uçdan-uca yoxlanması — real baza ilə.

Vahid testlər açarları ayrıca yoxlayır, bu isə bütün zənciri: eyni iş üç
mənbədən gələndə BİR sətir yaranmalı, digər mənbələr provenans kimi
qeyd olunmalıdır.

Test öz məlumatını yaradır və sonda təmizləyir — korpusa təsir etmir.
Baza əlçatmazdırsa test ötürülür (vahid testlər onsuz da işləyir).
"""

import uuid

import pytest
from sqlalchemy import func, select

from app import crud, models
from app.database import SessionLocal
from app.schemas import PaperIn

ABSTRACT = (
    "This synthetic record exercises cross-source identity resolution in the "
    "ingestion pipeline. It is long enough to pass the usability threshold so "
    "that chunking and embedding proceed exactly as they would for a real "
    "abstract, which is what makes the deduplication path meaningful to test."
)


@pytest.fixture
def db():
    try:
        session = SessionLocal()
        session.execute(select(models.Paper.id).limit(1))
    except Exception:
        pytest.skip("baza əlçatmazdır")
    yield session
    session.close()


@pytest.fixture
def marker():
    """Hər test öz unikal başlığı ilə işləyir ki, paralel qaçışlar toqquşmasın."""
    return f"Dedup Test {uuid.uuid4().hex[:10]} Cross Source Identity Resolution"


@pytest.fixture(autouse=True)
def cleanup(db, marker):
    yield
    for paper in db.scalars(select(models.Paper).where(models.Paper.title.like("Dedup Test %"))):
        db.delete(paper)
    db.commit()


def _paper(source: str, marker: str, **kw) -> PaperIn:
    return PaperIn(source=source, title=marker, abstract=ABSTRACT,
                   field_keys=["ai"], authors=["Test Author"], **kw)


def test_eyni_is_uc_menbeden_bir_setir_yaradir(db, marker):
    batch = [
        _paper("arxiv", marker, external_id="9999.11111", arxiv_id="9999.11111"),
        _paper("crossref", marker, external_id="10.9999/x", doi="10.9999/x"),
        _paper("doaj", marker.upper(), external_id="doaj-x"),   # yalnız başlıqla uyğunlaşır
    ]
    inserted, skipped, merged = crud.upsert_papers(db, batch)

    assert inserted == 1, "üç qeyd üçün yalnız bir sətir yaranmalıdır"
    assert merged == 2, "digər iki mənbə birləşdirilməlidir"

    rows = db.scalars(select(models.Paper).where(models.Paper.title.ilike(marker))).all()
    assert len(rows) == 1
    assert {s.source for s in rows[0].sources} == {"arxiv", "crossref", "doaj"}


def test_menbeler_bir_birini_zenginlesdirir(db, marker):
    """arXiv qeydində DOI yoxdur, Crossref onu gətirir — sətir tamamlanmalıdır."""
    crud.upsert_papers(db, [_paper("arxiv", marker, external_id="9999.22222", arxiv_id="9999.22222")])
    crud.upsert_papers(db, [_paper("crossref", marker, external_id="10.9999/y", doi="10.9999/y")])

    paper = db.scalars(select(models.Paper).where(models.Paper.title.ilike(marker))).one()
    assert paper.arxiv_id == "9999.22222"
    assert paper.doi == "10.9999/y"


def test_sahe_acarlari_birlesir(db, marker):
    crud.upsert_papers(db, [_paper("arxiv", marker, external_id="9999.33333", arxiv_id="9999.33333")])
    p2 = _paper("crossref", marker, external_id="10.9999/z", doi="10.9999/z")
    p2.field_keys = ["security"]
    crud.upsert_papers(db, [p2])

    paper = db.scalars(select(models.Paper).where(models.Paper.title.ilike(marker))).one()
    assert set(paper.field_keys) == {"ai", "security"}


def test_eyni_partiyanin_tekrari_yeni_setir_yaratmir(db, marker):
    batch = [_paper("arxiv", marker, external_id="9999.44444", arxiv_id="9999.44444")]

    first = crud.upsert_papers(db, batch)
    second = crud.upsert_papers(db, batch)

    assert first[0] == 1
    assert second[0] == 0, "təkrar yığım idempotent olmalıdır"

    count = db.scalar(
        select(func.count(models.Paper.id)).where(models.Paper.title.ilike(marker))
    )
    assert count == 1, "təkrar yığımdan sonra da yalnız bir sətir olmalıdır"


def test_dil_metnden_teyin_olunur(db, marker):
    ru = PaperIn(
        source="openalex", external_id="oa-ru-1", title="Криптографическая защита данных",
        abstract="Рассматривается проблема защиты информации в распределённых системах. "
                 "Предложен метод шифрования, устойчивый к атакам на основе анализа трафика, "
                 "и приведены результаты экспериментальной проверки на реальных данных.",
        field_keys=["security"],
    )
    crud.upsert_papers(db, [ru])
    paper = db.scalars(
        select(models.Paper).where(models.Paper.external_id == "oa-ru-1")
    ).one()
    assert paper.language == "ru"
    db.delete(paper)
    db.commit()
