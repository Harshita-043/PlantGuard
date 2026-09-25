"""Authenticated ownership dependencies for persisted resources."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.authorization import get_owned_resource
from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.user import User


def get_owned_analysis(
    analysis_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Analysis:
    """Resolve an analysis only for its authenticated owner."""
    return get_owned_resource(db, Analysis, analysis_id, current_user.id)
