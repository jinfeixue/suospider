"""Log API routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.service.log_service import LogService

router = APIRouter(prefix="/logs", tags=["Logs"], dependencies=[Depends(get_current_user)])


@router.get("")
def get_logs(
    run_id: int = Query(None),
    level: str = Query(None),
    keyword: str = Query(None),
    page: int = Query(1),
    page_size: int = Query(100),
    db: Session = Depends(get_db),
):
    data = LogService.get_logs(db, run_id=run_id, level=level, keyword=keyword,
                                      page=page, page_size=page_size)
    return {"code": 0, "data": data}


@router.get("/all")
def get_all_logs(
    task_id: int = Query(None),
    page: int = Query(1),
    page_size: int = Query(50),
    db: Session = Depends(get_db),
):
    data = LogService.get_all_logs(db, task_id=task_id, page=page, page_size=page_size)
    return {"code": 0, "data": data}
