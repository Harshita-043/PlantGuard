"""Authenticated, user-scoped dashboard metrics."""

import math
from collections import Counter
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.plant import Plant
from app.models.user import User
from app.schemas.analysis_lifecycle import AnalysisLifecycleResponse
from app.schemas.dashboard import DashboardMetricsResponse, HealthTrendPoint

router = APIRouter()


@router.get("/metrics", response_model=DashboardMetricsResponse)
def get_dashboard_metrics(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DashboardMetricsResponse:
    """Aggregate persisted analyses and plants belonging to the signed-in user."""
    status_counts = dict(
        db.execute(
            select(Analysis.status, func.count(Analysis.id))
            .where(Analysis.user_id == current_user.id)
            .group_by(Analysis.status)
        ).all()
    )
    total_analyses = sum(status_counts.values())
    total_plants = db.scalar(
        select(func.count(Plant.id)).where(Plant.user_id == current_user.id)
    ) or 0

    completed_results = db.scalars(
        select(Analysis.result_data)
        .where(
            Analysis.user_id == current_user.id,
            Analysis.status == "completed",
            Analysis.result_data.is_not(None),
        )
        .execution_options(yield_per=100)
    )
    healthy = 0
    diseased = 0
    inconclusive = 0
    health_scores: list[float] = []
    disease_distribution: Counter[str] = Counter()
    for result in completed_results:
        summary = result.get("plant_summary") if isinstance(result, dict) else None
        if not isinstance(summary, dict):
            inconclusive += 1
            continue

        health_status = summary.get("health_status")
        if health_status == "healthy":
            healthy += 1
        elif health_status in {"mildly_diseased", "severely_diseased"}:
            diseased += 1
        else:
            inconclusive += 1

        score = summary.get("overall_health_score")
        if (
            isinstance(score, (int, float))
            and not isinstance(score, bool)
            and math.isfinite(score)
            and 0 <= score <= 100
        ):
            health_scores.append(float(score))

        breakdown = summary.get("disease_breakdown")
        if isinstance(breakdown, dict):
            for label, count in breakdown.items():
                if (
                    isinstance(label, str)
                    and label
                    and isinstance(count, int)
                    and not isinstance(count, bool)
                    and count > 0
                ):
                    disease_distribution[label] += count

    completed_count = status_counts.get("completed", 0)
    inconclusive += max(0, completed_count - healthy - diseased - inconclusive)

    recent_analyses = db.scalars(
        select(Analysis)
        .where(Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
        .limit(8)
    ).all()
    recent_trend = db.scalars(
        select(Analysis)
        .where(
            Analysis.user_id == current_user.id,
            Analysis.status == "completed",
            Analysis.result_data.is_not(None),
        )
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
        .limit(30)
    ).all()

    trend: list[HealthTrendPoint] = []
    for analysis in reversed(recent_trend):
        result = analysis.result_data
        summary = result.get("plant_summary") if isinstance(result, dict) else None
        if not isinstance(summary, dict):
            continue
        score = summary.get("overall_health_score")
        health_status = summary.get("health_status")
        if (
            isinstance(score, (int, float))
            and not isinstance(score, bool)
            and math.isfinite(score)
            and 0 <= score <= 100
            and isinstance(health_status, str)
        ):
            severity = summary.get("average_severity_percentage")
            trend.append(
                HealthTrendPoint(
                    analysis_id=analysis.id,
                    timestamp=analysis.created_at,
                    health_score=float(score),
                    health_status=health_status,
                    severity_percentage=(
                        float(severity)
                        if isinstance(severity, (int, float))
                        and not isinstance(severity, bool)
                        and math.isfinite(severity)
                        and 0 <= severity <= 100
                        else None
                    ),
                )
            )

    return DashboardMetricsResponse(
        total_analyses=total_analyses,
        healthy_analyses=healthy,
        diseased_analyses=diseased,
        inconclusive_analyses=inconclusive,
        failed_analyses=status_counts.get("failed", 0),
        total_plants=total_plants,
        average_health_score=(
            sum(health_scores) / len(health_scores) if health_scores else None
        ),
        disease_distribution=dict(disease_distribution),
        recent_scans=[
            AnalysisLifecycleResponse(
                analysis_id=analysis.id,
                plant_id=analysis.plant_id,
                status=analysis.status,
                created_at=analysis.created_at,
                image_content_type=analysis.image_content_type,
                image_size_bytes=analysis.image_size_bytes,
                result_available=analysis.result_data is not None,
                result=analysis.result_data,
                failure=analysis.failure_data,
            )
            for analysis in recent_analyses
        ],
        health_trend=trend,
    )
