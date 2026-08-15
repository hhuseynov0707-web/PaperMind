"""İstifadəçinin kitabxanası — «research memory»nin ilk qatı.

Strategiya sənədi haqlıdır: saxlanan məqalə tək başına fərqləndirici deyil.
Amma o, hər şeyin üzərində quruldugu bazadır — layihələr, öz korpusu üzrə
sintez və PDF hamısı «istifadəçinin öz məcmusu» anlayışını tələb edir.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import auth, models, plans
from ..database import get_db
from ..schemas import PaperOut, SavePaperRequest, SavedPaperOut

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("", response_model=list[SavedPaperOut])
def list_saved(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_user),
):
    rows = (
        db.query(models.SavedPaper)
        .filter(models.SavedPaper.user_id == user.id)
        .order_by(models.SavedPaper.created_at.desc())
        .all()
    )
    return [
        SavedPaperOut(
            paper=_paper_out(r.paper), note=r.note, created_at=r.created_at
        )
        for r in rows
        if r.paper is not None
    ]


@router.post("", response_model=SavedPaperOut, status_code=201)
def save_paper(
    req: SavePaperRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_capability(plans.SAVE)),
):
    paper = db.get(models.Paper, req.paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Məqalə tapılmadı.")

    existing = (
        db.query(models.SavedPaper)
        .filter(
            models.SavedPaper.user_id == user.id,
            models.SavedPaper.paper_id == req.paper_id,
        )
        .first()
    )
    if existing is not None:
        # Təkrar saxlama xəta deyil — qeydi yeniləyib mövcud sətri qaytarırıq.
        if req.note is not None:
            existing.note = req.note
            db.commit()
        return SavedPaperOut(
            paper=_paper_out(paper), note=existing.note, created_at=existing.created_at
        )

    limit = plans.get_plan(user.plan).library_limit
    used = db.query(models.SavedPaper).filter(models.SavedPaper.user_id == user.id).count()
    if used >= limit:
        # 402 + strukturlaşdırılmış detal: interfeys bunu ümumi xətadan ayırıb
        # kontekstli yüksəltmə təklifi göstərə bilsin (§20).
        raise HTTPException(
            status_code=402,
            detail={
                "error": "library_full",
                "limit": limit,
                "plan": user.plan,
                "message": f"Kitabxana doldu ({limit} məqalə).",
            },
        )

    row = models.SavedPaper(user_id=user.id, paper_id=req.paper_id, note=req.note)
    db.add(row)
    db.commit()
    db.refresh(row)
    return SavedPaperOut(paper=_paper_out(paper), note=row.note, created_at=row.created_at)


@router.delete("/{paper_id}", status_code=204)
def remove_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_user),
):
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
