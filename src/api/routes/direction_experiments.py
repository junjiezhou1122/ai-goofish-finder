"""
Finder 实验路由。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import (
    get_direction_experiment_service,
    get_direction_recommendation_service,
    get_process_service,
    get_scheduler_service,
    get_task_generation_service,
    get_task_service,
)
from src.domain.models.task import TaskGenerateRequest
from src.services.direction_experiment_service import DirectionExperimentService
from src.services.direction_recommendation_service import DirectionRecommendationService
from src.services.process_service import ProcessService
from src.services.scheduler_service import SchedulerService
from src.services.task_generation_runner import build_task_create, reload_scheduler
from src.services.task_generation_service import TaskGenerationService
from src.services.task_service import TaskService


router = APIRouter(prefix="/api/finder/directions", tags=["finder-experiments"])


@router.get("/{direction_id}/experiments", response_model=dict)
async def get_direction_experiments(
    direction_id: int,
    service: DirectionExperimentService = Depends(get_direction_experiment_service),
):
    return {"items": await service.list_direction_experiments(direction_id)}


@router.post("/{direction_id}/experiments", response_model=dict)
async def create_experiment_from_recommendation(
    direction_id: int,
    recommendation_id: int,
    task_service: TaskService = Depends(get_task_service),
    experiment_service: DirectionExperimentService = Depends(get_direction_experiment_service),
    recommendation_service: DirectionRecommendationService = Depends(get_direction_recommendation_service),
    scheduler_service: SchedulerService = Depends(get_scheduler_service),
    generation_service: TaskGenerationService = Depends(get_task_generation_service),
    process_service: ProcessService = Depends(get_process_service),
):
    """
    从推荐词创建实验任务。
    内部调用 /tasks/generate 流程，并注册 experiment 关联。
    """
    # 获取推荐词详情
    recommendation = await recommendation_service.get_recommendation(recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="推荐词不存在")
    if recommendation["direction_id"] != direction_id:
        raise HTTPException(status_code=400, detail="推荐词不属于该方向")

    # 构建任务生成请求
    keyword = str(recommendation["keyword"] or "").strip()
    task_name = keyword + " 监控"
    req = TaskGenerateRequest(
        task_name=task_name,
        keyword=keyword,
        description=f"来源：Finder 推荐 | 推荐词：{keyword} | 推荐动作：{recommendation.get('recommended_action', 'unknown')}",
        finder_direction_id=direction_id,
        finder_candidate_id=recommendation.get("candidate_id"),
        finder_recommendation_id=recommendation_id,
        decision_mode="ai",
        max_pages=3,
        personal_only=True,
        cron=None,
    )

    # 直接构建 criteria 文件路径（不调用 AI 生成），创建任务
    safe_keyword = "".join(
        c for c in keyword.lower().replace(" ", "_")
        if c.isalnum() or c in "_-"
    ).rstrip()
    criteria_file = f"prompts/{safe_keyword}_criteria.txt"

    task = await task_service.create_task(build_task_create(req, criteria_file))
    await reload_scheduler(task_service, scheduler_service)

    # 注册 experiment 关联
    experiment = await experiment_service.create_task_experiment(
        direction_id=direction_id,
        candidate_id=recommendation.get("candidate_id"),
        recommendation_id=recommendation_id,
        task=task,
    )
    if experiment.get("id") and process_service:
        process_service.set_task_experiment(task.id, int(experiment["id"]))

    # 更新推荐状态为 accepted
    await recommendation_service.update_recommendation_status(recommendation_id, "accepted")

    return {"experiment": experiment, "task": task, "recommendation": recommendation}
