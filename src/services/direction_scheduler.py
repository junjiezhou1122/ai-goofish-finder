"""
Finder 方向定时刷新调度器。

负责定时触发方向的扩词 → evidence聚合 → 推荐刷新的完整管道。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.infrastructure.persistence.sqlite_direction_candidate_repository import (
    SqliteDirectionCandidateRepository,
)
from src.infrastructure.persistence.sqlite_direction_repository import (
    SqliteDirectionRepository,
)
from src.services.direction_candidate_insight_service import (
    DirectionCandidateInsightService,
)
from src.services.direction_candidate_service import DirectionCandidateService
from src.services.direction_recommendation_service import (
    DirectionRecommendationService,
)

if TYPE_CHECKING:
    from src.domain.models.direction import Direction

logger = logging.getLogger(__name__)

# 全局调度器实例（延迟初始化）
_scheduler: AsyncIOScheduler | None = None


def _get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        try:
            _scheduler.start()
            logger.info("Direction 调度器已启动")
        except RuntimeError as exc:
            if "event loop" in str(exc).lower():
                logger.warning("Direction 调度器未能在测试环境启动（event loop 不可用）")
            else:
                raise
    return _scheduler


def register_direction_refresh(
    direction: "Direction",
    *,
    cron: str = "0 */6 * * *",
) -> None:
    """
    为方向注册定时刷新任务。

    默认每 6 小时运行一次：扩词(规则+共现) → evidence+state聚合 → 推荐刷新。

    Args:
        direction: 方向领域模型
        cron: cron 表达式，默认为 "0 */6 * * *"
    """
    scheduler = _get_scheduler()
    job_id = f"finder_refresh_{direction.id}"

    # 取消已有任务（防止重复注册）
    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)

    scheduler.add_job(
        _refresh_pipeline,
        "cron",
        minute=cron.split()[0],
        hour=cron.split()[1] if len(cron.split()) > 1 else None,
        day=cron.split()[2] if len(cron.split()) > 2 else "*",
        month=cron.split()[3] if len(cron.split()) > 3 else "*",
        day_of_week=cron.split()[4] if len(cron.split()) > 4 else "*",
        timezone="Asia/Shanghai",
        args=[direction.id],
        id=job_id,
        name=f"Finder刷新: {direction.name}",
        replace_existing=True,
    )
    logger.info(f"已为方向 '{direction.name}' (id={direction.id}) 注册刷新任务，cron={cron}")


def unregister_direction_refresh(direction_id: int) -> None:
    """移除方向的定时刷新任务。"""
    scheduler = _get_scheduler()
    job_id = f"finder_refresh_{direction_id}"
    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)
        logger.info(f"已移除方向 id={direction_id} 的刷新任务")


def shutdown_scheduler() -> None:
    """关闭调度器（应用退出时调用）。"""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("Direction 调度器已关闭")


async def _refresh_pipeline(direction_id: int) -> None:
    """
    方向刷新完整管道。

    执行顺序：
    1. 候选词列表查询（从 DB）
    2. evidence + opportunity_state 聚合写入
    3. 推荐刷新
    """
    logger.info(f"[Finder刷新] 开始刷新方向 id={direction_id}")

    try:
        # 初始化服务
        candidate_repo = SqliteDirectionCandidateRepository()
        direction_repo = SqliteDirectionRepository()
        candidate_service = DirectionCandidateService(
            candidate_repository=candidate_repo,
            direction_repository=direction_repo,
        )
        insight_service = DirectionCandidateInsightService()
        recommendation_service = DirectionRecommendationService()

        # 1. 候选词列表
        candidates = await candidate_service.list_candidates(direction_id)
        if not candidates:
            logger.info(f"[Finder刷新] 方向 id={direction_id} 无候选词，跳过")
            return

        logger.info(f"[Finder刷新] 找到 {len(candidates)} 个候选词，开始聚合 evidence...")

        # 2. evidence + state 聚合
        enriched = await insight_service.refresh_direction_candidates(direction_id, candidates)
        logger.info(f"[Finder刷新] evidence 聚合完成，{len(enriched)} 个候选词已更新")

        # 3. 推荐刷新
        await recommendation_service.refresh_direction_recommendations(direction_id, enriched)
        logger.info(f"[Finder刷新] 推荐刷新完成")

    except Exception as exc:
        logger.error(f"[Finder刷新] 方向 id={direction_id} 刷新失败: {exc}", exc_info=True)
