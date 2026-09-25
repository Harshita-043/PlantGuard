"""Reusable ownership-scoped resource lookup helpers."""

from typing import Any, TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

OwnedResource = TypeVar("OwnedResource")


def get_owned_resource(
    db: Session,
    model: type[OwnedResource],
    resource_id: UUID,
    owner_id: UUID,
) -> OwnedResource:
    """Load a resource only when it belongs to ``owner_id``.

    The owner condition is part of the database query, so missing and foreign
    resources have the same 404 response and never return another user's row.
    Models passed here must define UUID ``id`` and ``user_id`` columns.
    """
    resource_model: Any = model
    resource = db.scalar(
        select(resource_model).where(
            resource_model.id == resource_id,
            resource_model.user_id == owner_id,
        )
    )
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return resource
