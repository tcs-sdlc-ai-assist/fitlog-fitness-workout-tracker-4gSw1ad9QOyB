import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Optional

from sqlalchemy.orm import Session

from models.user import User
from utils.security import hash_password, verify_password


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username.strip().lower()).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.strip().lower()).first()


def register_user(
    db: Session,
    username: str,
    email: str,
    display_name: str,
    password: str,
    role: str = "user",
) -> User:
    username = username.strip().lower()
    email = email.strip().lower()
    display_name = display_name.strip()

    existing_username = get_user_by_username(db, username)
    if existing_username:
        raise ValueError("Username already exists.")

    existing_email = get_user_by_email(db, email)
    if existing_email:
        raise ValueError("Email already exists.")

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    if not display_name:
        raise ValueError("Display name is required.")

    hashed = hash_password(password)

    user = User(
        username=username,
        email=email,
        display_name=display_name,
        password_hash=hashed,
        role=role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def update_user_profile(
    db: Session,
    user_id: int,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
) -> User:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise ValueError("User not found.")

    if display_name is not None:
        display_name = display_name.strip()
        if not display_name:
            raise ValueError("Display name cannot be empty.")
        if len(display_name) > 100:
            raise ValueError("Display name must be 100 characters or fewer.")
        user.display_name = display_name

    if email is not None:
        email = email.strip().lower()
        if not email:
            raise ValueError("Email cannot be empty.")
        existing = get_user_by_email(db, email)
        if existing and existing.id != user_id:
            raise ValueError("Email already in use by another account.")
        user.email = email

    db.commit()
    db.refresh(user)
    return user


def change_password(
    db: Session,
    user_id: int,
    current_password: str,
    new_password: str,
) -> User:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise ValueError("User not found.")

    if not verify_password(current_password, user.password_hash):
        raise ValueError("Current password is incorrect.")

    if len(new_password) < 8:
        raise ValueError("New password must be at least 8 characters.")

    if len(new_password) > 128:
        raise ValueError("New password must be 128 characters or fewer.")

    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> None:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise ValueError("User not found.")
    db.delete(user)
    db.commit()


def get_all_users(db: Session) -> list:
    return db.query(User).order_by(User.created_at.desc()).all()