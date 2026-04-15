from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workout_id = Column(Integer, ForeignKey("workouts.id"), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False, index=True)
    sort_order = Column(Integer, nullable=False, default=1)
    notes = Column(String, nullable=True, default="")

    workout = relationship("Workout", back_populates="exercises", lazy="selectin")
    exercise = relationship("Exercise", back_populates="workout_exercises", lazy="selectin")
    sets = relationship(
        "Set",
        back_populates="workout_exercise",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="Set.set_number",
    )