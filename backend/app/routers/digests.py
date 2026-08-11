from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..schemas import DigestIn, DigestOut
from ..security import require_admin_key

router = APIRouter(prefix="/api", tags=["digests"])


@router.post(
    "/digests", response_model=DigestOut, status_code=201,
    dependencies=[Depends(require_admin_key)],
)
def create_digest(payload: DigestIn, db: Session = Depends(get_db)):
    """n8n weekly_digest workflow-u LLM icmalını bura yazır (həftə üzrə upsert)."""
    return crud.upsert_digest(db, payload.week_start, payload.content)


@router.get("/digests/latest", response_model=DigestOut | None)
def latest_digest(db: Session = Depends(get_db)):
    return crud.latest_digest(db)
