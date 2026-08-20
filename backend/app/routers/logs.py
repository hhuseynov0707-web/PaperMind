from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..schemas import ErrorIn, ErrorOut, IngestRunOut, QaItemOut
from ..security import require_admin_key

# Mühafizə ROUTER səviyyəsindədir, hər endpoint üzərində ayrıca yox.
#
# Əvvəl yalnız YAZMA (POST /logs/error) açar tələb edirdi, üç OXUMA isə
# açıq idi — yəni `GET /api/logs/questions` internetdə hər kəsə bütün
# istifadəçi suallarını qaytarırdı. Səhv ona görə baş verdi ki, qorunma
# endpoint-in seçimi idi: birini yazanda əlavə etməyi unutmaq kifayətdir.
#
# İndi qorunma qabın xüsusiyyətidir: bu fayla sonradan əlavə olunan hər
# endpoint də avtomatik açar tələb edir. Loglar əməliyyat məlumatıdır,
# istisnasız hamısı daxili istifadə üçündür.
router = APIRouter(
    prefix="/api",
    tags=["logs"],
    dependencies=[Depends(require_admin_key)],
)


@router.post("/logs/error", response_model=ErrorOut, status_code=201)
def add_error(payload: ErrorIn, db: Session = Depends(get_db)):
    """n8n error_handler workflow-u xətaları bura göndərir."""
    return crud.add_error(db, payload.workflow, payload.node, payload.message)


@router.get("/logs/errors", response_model=list[ErrorOut])
def list_errors(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    return crud.recent_errors(db, limit)


@router.get("/logs/ingest-runs", response_model=list[IngestRunOut])
def list_ingest_runs(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    return crud.recent_ingest_runs(db, limit)


@router.get("/logs/questions", response_model=list[QaItemOut])
def list_questions(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    return crud.recent_questions(db, limit)
