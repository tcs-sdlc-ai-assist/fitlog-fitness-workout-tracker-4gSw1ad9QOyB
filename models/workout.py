from datetime import date, datetime

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from database import Base


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    workout_date = Column(Date, nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True, default="")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="workouts", lazy="selectin")
    workout_exercises = relationship(
        "WorkoutExercise",
        back_populates="workout",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.sort_order",
    )

    def __repr__(self):
        return f"<Workout(id={self.id}, name='{self.name}', date={self.workout_date})>"