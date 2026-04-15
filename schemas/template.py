from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class TemplateExerciseCreate(BaseModel):
    exercise_id: int
    sort_order: int = 1
    default_sets: int = 3
    default_reps: int = 10
    default_weight: Optional[float] = None
    notes: Optional[str] = None

    @field_validator("exercise_id")
    @classmethod
    def exercise_id_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("exercise_id must be a positive integer")
        return v

    @field_validator("sort_order")
    @classmethod
    def sort_order_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("sort_order must be at least 1")
        return v

    @field_validator("default_sets")
    @classmethod
    def default_sets_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("default_sets must be at least 1")
        return v

    @field_validator("default_reps")
    @classmethod
    def default_reps_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("default_reps must be at least 1")
        return v

    @field_validator("default_weight")
    @classmethod
    def default_weight_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("default_weight must be non-negative")
        return v


class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_system: bool = False
    exercises: list[TemplateExerciseCreate] = []

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Template name is required")
        if len(v) > 200:
            raise ValueError("Template name must be 200 characters or fewer")
        return v

    @field_validator("description")
    @classmethod
    def description_strip(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_system: Optional[bool] = None
    exercises: Optional[list[TemplateExerciseCreate]] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Template name cannot be empty")
            if len(v) > 200:
                raise ValueError("Template name must be 200 characters or fewer")
        return v

    @field_validator("description")
    @classmethod
    def description_strip(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class TemplateExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int
    exercise_id: int
    sort_order: int
    default_sets: int
    default_reps: int
    default_weight: Optional[float] = None
    notes: Optional[str] = None
    exercise_name: Optional[str] = None


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    is_system: bool = False
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime
    exercises: list[TemplateExerciseResponse] = []