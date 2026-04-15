from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class MeasurementCreate(BaseModel):
    measurement_date: date
    weight: Optional[float] = None
    body_fat_pct: Optional[float] = None
    chest: Optional[float] = None
    waist: Optional[float] = None
    hips: Optional[float] = None
    biceps: Optional[float] = None
    thighs: Optional[float] = None
    notes: Optional[str] = None

    @field_validator("weight", "body_fat_pct", "chest", "waist", "hips", "biceps", "thighs", mode="before")
    @classmethod
    def validate_positive(cls, v: Optional[float], info) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError(f"{info.field_name} must be a non-negative number")
        return v

    @field_validator("body_fat_pct", mode="before")
    @classmethod
    def validate_body_fat_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 100):
            raise ValueError("body_fat_pct must be between 0 and 100")
        return v


class MeasurementUpdate(BaseModel):
    measurement_date: Optional[date] = None
    weight: Optional[float] = None
    body_fat_pct: Optional[float] = None
    chest: Optional[float] = None
    waist: Optional[float] = None
    hips: Optional[float] = None
    biceps: Optional[float] = None
    thighs: Optional[float] = None
    notes: Optional[str] = None

    @field_validator("weight", "body_fat_pct", "chest", "waist", "hips", "biceps", "thighs", mode="before")
    @classmethod
    def validate_positive(cls, v: Optional[float], info) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError(f"{info.field_name} must be a non-negative number")
        return v

    @field_validator("body_fat_pct", mode="before")
    @classmethod
    def validate_body_fat_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 100):
            raise ValueError("body_fat_pct must be between 0 and 100")
        return v


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    measurement_date: date
    weight: Optional[float] = None
    body_fat_pct: Optional[float] = None
    chest: Optional[float] = None
    waist: Optional[float] = None
    hips: Optional[float] = None
    biceps: Optional[float] = None
    thighs: Optional[float] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TrendSummary(BaseModel):
    metric: str
    current_value: Optional[float] = None
    previous_value: Optional[float] = None
    delta: Optional[float] = None
    delta_pct: Optional[float] = None
    trend_direction: Optional[str] = None