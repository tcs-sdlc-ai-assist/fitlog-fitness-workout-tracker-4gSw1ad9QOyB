from sqlalchemy import Column, Integer, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class ExerciseSet(Base):
    __tablename__ = "sets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workout_exercise_id = Column(Integer, ForeignKey("workout_exercises.id"), nullable=False, index=True)
    set_number = Column(Integer, nullable=False)
    weight = Column(Float, nullable=True)
    reps = Column(Integer, nullable=False)
    is_completed = Column(Boolean, default=True, nullable=False)
    is_pr = Column(Boolean, default=False, nullable=False)

    workout_exercise = relationship("WorkoutExercise", back_populates="sets", lazy="selectin")

    def __repr__(self):
        return f"<ExerciseSet(id={self.id}, set_number={self.set_number}, weight={self.weight}, reps={self.reps})>"