from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class ExerciseCreate(BaseModel):
    name: str
    muscle_group: str
    equipment: Optional[str] = None
    instructions: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Exercise name is required.")
        return v

    @field_validator("muscle_group")
    @classmethod
    def muscle_group_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Muscle group is required.")
        return v


class ExerciseUpdate(BaseModel):
    name: Optional[str] = None
    muscle_group: Optional[str] = None
    equipment: Optional[str] = None
    instructions: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Exercise name cannot be empty.")
        return v

    @field_validator("muscle_group")
    @classmethod
    def muscle_group_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Muscle group cannot be empty.")
        return v


class ExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    muscle_group: str
    equipment: Optional[str] = None
    instructions: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ExerciseFilter(BaseModel):
    search: Optional[str] = None
    muscle_group: Optional[str] = None
    equipment: Optional[str] = None
    page: int = 1
    per_page: int = 20

    @field_validator("page")
    @classmethod
    def page_must_be_positive(cls, v: int) -> int:
        if v < 1:
            return 1
        return v

    @field_validator("per_page")
    @classmethod
    def per_page_must_be_reasonable(cls, v: int) -> int:
        if v < 1:
            return 20
        if v > 100:
            return 100
        return v