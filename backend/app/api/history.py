"""
历史记录相关 API 路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.history_service import history_service

router = APIRouter(prefix="/api/history", tags=["历史记录"])


@router.get("/records")
async def get_history_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取历史检测记录列表（分页）"""
    tasks, total = history_service.get_history_records(db=db, page=page, page_size=page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": history_service.format_history_response(tasks),
    }


@router.get("/statistics")
async def get_history_statistics(db: Session = Depends(get_db)):
    """获取历史记录统计信息"""
    return history_service.get_history_statistics(db=db)