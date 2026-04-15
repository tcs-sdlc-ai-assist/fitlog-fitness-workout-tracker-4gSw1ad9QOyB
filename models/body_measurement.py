from datetime import date, datetime

from sqlalchemy import Column, Integer, Float, Date, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship

from database import Base


class BodyMeasurement(Base):
    __tablename__ = "body_measurements"

    __table_args__ = (
        UniqueConstraint("user_id", "measurement_date", name="uq_user_measurement_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    measurement_date = Column(Date, nullable=False, index=True)
    weight = Column(Float, nullable=True)
    body_fat_pct = Column(Float, nullable=True)
    chest = Column(Float, nullable=True)
    waist = Column(Float, nullable=True)
    hips = Column(Float, nullable=True)
    left_arm = Column(Float, nullable=True)
    right_arm = Column(Float, nullable=True)
    left_thigh = Column(Float, nullable=True)
    right_thigh = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="measurements", lazy="selectin")