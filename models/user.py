from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    workouts = relationship(
        "Workout",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    templates = relationship(
        "WorkoutTemplate",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    measurements = relationship(
        "BodyMeasurement",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    personal_records = relationship(
        "PersonalRecord",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"