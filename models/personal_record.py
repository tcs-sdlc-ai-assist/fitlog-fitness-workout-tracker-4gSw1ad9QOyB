import datetime

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from database import Base


class PersonalRecord(Base):
    __tablename__ = "personal_records"
    __table_args__ = (
        UniqueConstraint("user_id", "exercise_id", "record_type", name="uq_user_exercise_record_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False, index=True)
    record_type = Column(String, nullable=False)  # 'weight', 'reps', 'volume'
    value = Column(Float, nullable=False)
    achieved_at = Column(DateTime, nullable=True)
    set_id = Column(Integer, ForeignKey("sets.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="personal_records", lazy="selectin")
    exercise = relationship("Exercise", back_populates="personal_records", lazy="selectin")