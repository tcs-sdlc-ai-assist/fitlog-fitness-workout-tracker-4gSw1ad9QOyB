from sqlalchemy import Column, Integer, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from database import Base


class TemplateExercise(Base):
    __tablename__ = "template_exercises"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("workout_templates.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    sort_order = Column(Integer, nullable=False, default=1)
    default_sets = Column(Integer, nullable=False, default=3)
    default_reps = Column(Integer, nullable=False, default=10)
    default_weight = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    template = relationship("WorkoutTemplate", back_populates="exercises", lazy="selectin")
    exercise = relationship("Exercise", back_populates="template_exercises", lazy="selectin")