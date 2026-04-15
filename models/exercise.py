from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True, index=True)
    muscle_group = Column(String(100), nullable=False, index=True)
    equipment = Column(String(100), nullable=True)
    instructions = Column(Text, nullable=True)
    is_system = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    workout_exercises = relationship(
        "WorkoutExercise",
        back_populates="exercise",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    template_exercises = relationship(
        "TemplateExercise",
        back_populates="exercise",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    personal_records = relationship(
        "PersonalRecord",
        back_populates="exercise",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Exercise(id={self.id}, name='{self.name}', muscle_group='{self.muscle_group}')>"