from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class SetCreate(BaseModel):
    set_number: int
    weight: Optional[float] = None
    reps: int
    is_completed: bool = True

    @field_validator("set_number")
    @classmethod
    def set_number_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Set number must be at least 1")
        return v

    @field_validator("reps")
    @classmethod
    def reps_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Reps must be non-negative")
        return v

    @field_validator("weight")
    @classmethod
    def weight_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Weight must be non-negative")
        return v


class SetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workout_exercise_id: int
    set_number: int
    weight: Optional[float] = None
    reps: int
    is_completed: bool = True
    is_pr: bool = False


class WorkoutExerciseCreate(BaseModel):
    exercise_id: int
    sort_order: int = 1
    notes: Optional[str] = ""
    sets: list[SetCreate]

    @field_validator("sets")
    @classmethod
    def at_least_one_set(cls, v: list[SetCreate]) -> list[SetCreate]:
        if not v or len(v) == 0:
            raise ValueError("Each exercise must have at least one set")
        return v

    @field_validator("exercise_id")
    @classmethod
    def exercise_id_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Exercise ID must be a positive integer")
        return v


class WorkoutExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workout_id: int
    exercise_id: int
    sort_order: int
    notes: Optional[str] = ""
    sets: list[SetResponse] = []
    exercise_name: Optional[str] = None


class WorkoutCreate(BaseModel):
    name: str
    workout_date: date
    duration_minutes: Optional[int] = None
    notes: Optional[str] = ""
    exercises: list[WorkoutExerciseCreate]

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Workout name is required")
        return v

    @field_validator("exercises")
    @classmethod
    def at_least_one_exercise(cls, v: list[WorkoutExerciseCreate]) -> list[WorkoutExerciseCreate]:
        if not v or len(v) == 0:
            raise ValueError("At least one exercise is required")
        return v

    @field_validator("duration_minutes")
    @classmethod
    def duration_non_negative(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Duration must be non-negative")
        return v


class WorkoutUpdate(BaseModel):
    name: Optional[str] = None
    workout_date: Optional[date] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    exercises: Optional[list[WorkoutExerciseCreate]] = None

    @field_validator("name")
    @classmethod
    def name_not_empty_if_provided(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Workout name cannot be empty")
        return v

    @field_validator("exercises")
    @classmethod
    def at_least_one_exercise_if_provided(cls, v: Optional[list[WorkoutExerciseCreate]]) -> Optional[list[WorkoutExerciseCreate]]:
        if v is not None and len(v) == 0:
            raise ValueError("At least one exercise is required")
        return v

    @field_validator("duration_minutes")
    @classmethod
    def duration_non_negative(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Duration must be non-negative")
        return v


class WorkoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    workout_date: date
    duration_minutes: Optional[int] = None
    notes: Optional[str] = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    exercises: list[WorkoutExerciseResponse] = []


class WorkoutListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    workout_date: date
    duration_minutes: Optional[int] = None
    notes: Optional[str] = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    exercise_count: Optional[int] = 0
    total_sets: Optional[int] = 0


class WorkoutPaginatedResponse(BaseModel):
    items: list[WorkoutListResponse]
    total: int
    page: int
    per_page: int
    total_pages: int