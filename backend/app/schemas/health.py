"""Schemas for static API health responses."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    message: str
