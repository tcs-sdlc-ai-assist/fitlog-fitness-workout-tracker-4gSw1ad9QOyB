import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from utils.dependencies import get_current_user, get_flash_messages
from utils.security import verify_password, hash_password
from jinja2 import Environment, FileSystemLoader

from starlette.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

router = APIRouter()


@router.get("/profile")
def profile_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    messages = get_flash_messages(request)
    return templates.TemplateResponse(
        request,
        "profile/index.html",
        context={
            "user": user,
            "messages": messages,
            "error": None,
            "success": None,
            "password_error": None,
            "password_success": None,
        },
    )


@router.post("/profile")
def update_profile(
    request: Request,
    display_name: str = Form(...),
    email: str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    error = None
    success = None

    display_name = display_name.strip()
    email = email.strip().lower()

    if not display_name:
        error = "Display name cannot be empty."
    elif len(display_name) > 100:
        error = "Display name must be 100 characters or fewer."
    elif not email:
        error = "Email cannot be empty."
    else:
        existing_email_user = db.query(User).filter(
            User.email == email,
            User.id != user.id,
        ).first()
        if existing_email_user:
            error = "Email already in use by another account."
        else:
            user.display_name = display_name
            user.email = email
            try:
                db.commit()
                db.refresh(user)
                success = "Profile updated successfully."
            except Exception:
                db.rollback()
                error = "An error occurred while updating your profile."

    messages = get_flash_messages(request)
    return templates.TemplateResponse(
        request,
        "profile/index.html",
        context={
            "user": user,
            "messages": messages,
            "error": error,
            "success": success,
            "password_error": None,
            "password_success": None,
        },
    )


@router.post("/profile/password")
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_new_password: str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    password_error = None
    password_success = None

    if not current_password:
        password_error = "Current password is required."
    elif not verify_password(current_password, user.password_hash):
        password_error = "Current password is incorrect."
    elif len(new_password) < 8:
        password_error = "New password must be at least 8 characters."
    elif len(new_password) > 128:
        password_error = "New password must be 128 characters or fewer."
    elif new_password != confirm_new_password:
        password_error = "New passwords do not match."
    else:
        user.password_hash = hash_password(new_password)
        try:
            db.commit()
            db.refresh(user)
            password_success = "Password updated successfully."
        except Exception:
            db.rollback()
            password_error = "An error occurred while updating your password."

    messages = get_flash_messages(request)
    return templates.TemplateResponse(
        request,
        "profile/index.html",
        context={
            "user": user,
            "messages": messages,
            "error": None,
            "success": None,
            "password_error": password_error,
            "password_success": password_success,
        },
    )