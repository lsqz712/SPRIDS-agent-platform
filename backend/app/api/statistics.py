"""
检测统计 API 路由
- GET /api/statistics/overview             总览统计
- GET /api/statistics/daily-trend          每日检测趋势
- GET /api/statistics/defect-distribution   缺陷类型分布
- GET /api/statistics/scene-distribution    各场景检测次数

所有统计接口均需要登录认证
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_active_user
from app.api.utils import success_response
from app.entity.db_models import User
from app.entity.schemas import (
    OverviewStatistics,
    DailyTrendItem,
    DefectDistributionItem,
    DefectDistributionResponse,
    SceneDistributionItem,
)
from app.services.statistics_service import statistics_service

router = APIRouter(prefix="/api/statistics", tags=["检测统计"])


@router.get("/overview")
async def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    总览统计

    返回系统整体检测数据概览：
    - 总任务数、完成任务数、失败任务数
    - 总检测图像数、总检测目标数
    - 平均推理耗时
    - 各类别缺陷分布
    - 各复判状态分布
    - 各严重等级分布
    - 各场景分布
    """
    data = statistics_service.get_overview(db=db)
    return success_response(data=OverviewStatistics(**data))


@router.get("/daily-trend")
async def get_daily_trend(
    days: int = Query(default=30, ge=1, le=365, description="统计最近 N 天"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    每日检测趋势
    - 按日期维度统计最近 N 天的任务数、检测图像数、检测目标数
    """
    raw_data = statistics_service.get_daily_trend(db=db, days=days)
    items = [DailyTrendItem(**item) for item in raw_data]
    return success_response(data={"days": days, "items": items})


@router.get("/defect-distribution")
async def get_defect_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    缺陷类型分布
    - 按检测结果的 class_name 维度统计各类别缺陷数量
    - 返回缺陷类型列表及总数
    """
    raw_data = statistics_service.get_defect_distribution(db=db)
    items = [DefectDistributionItem(**item) for item in raw_data["items"]]
    data = DefectDistributionResponse(items=items, total=raw_data["total"])
    return success_response(data=data)


@router.get("/scene-distribution")
async def get_scene_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    各场景检测次数统计
    - 按检测场景维度统计已完成的任务数、图像数、目标数
    """
    raw_data = statistics_service.get_scene_distribution(db=db)
    items = [SceneDistributionItem(**item) for item in raw_data]
    return success_response(data={"items": items})
