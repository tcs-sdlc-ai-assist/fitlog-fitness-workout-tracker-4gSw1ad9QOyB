import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Request, Form, Depends, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from services.auth_service import (
    register_user,
    authenticate_user,
    get_user_by_username,
    get_user_by_email,
)
from utils.security import create_access_token
from utils.dependencies import get_optional_user

router = APIRouter(prefix="/auth", tags=["auth"])

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/register")
def register_page(
    request: Request,
    user=Depends(get_optional_user),
):
    if user is not None:
        if user.role == "admin":
            return RedirectResponse(url="/admin/dashboard", status_code=302)
        return RedirectResponse(url="/dashboard", status_code=302)

    return templates.TemplateResponse(
        request,
        "auth/register.html",
        context={
            "error": None,
            "errors": None,
            "form_data": None,
        },
    )


@router.post("/register")
def register_submit(
    request: Request,
    display_name: str = Form(""),
    email: str = Form(""),
    username: str = Form(""),
    password: str = Form(""),
    confirm_password: str = Form(""),
    db: Session = Depends(get_db),
):
    form_data = {
        "display_name": display_name,
        "email": email,
        "username": username,
    }

    errors = []

    display_name = display_name.strip()
    email = email.strip().lower()
    username = username.strip().lower()

    if not display_name:
        errors.append("Display name is required.")
    elif len(display_name) > 100:
        errors.append("Display name must be 100 characters or fewer.")

    if not email:
        errors.append("Email is required.")

    if not username:
        errors.append("Username is required.")
    elif len(username) < 3:
        errors.append("Username must be at least 3 characters.")
    elif len(username) > 50:
        errors.append("Username must be 50 characters or fewer.")
    elif not all(c.isalnum() or c in ("_", "-") for c in username):
        errors.append("Username may only contain letters, numbers, underscores, and hyphens.")

    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    elif len(password) > 128:
        errors.append("Password must be 128 characters or fewer.")

    if not confirm_password:
        errors.append("Please confirm your password.")
    elif password and confirm_password != password:
        errors.append("Passwords do not match.")

    if errors:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "error": None,
                "errors": errors,
                "form_data": form_data,
            },
            status_code=400,
        )

    existing_username = get_user_by_username(db, username)
    if existing_username:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "error": "Username already exists.",
                "errors": None,
                "form_data": form_data,
            },
            status_code=400,
        )

    existing_email = get_user_by_email(db, email)
    if existing_email:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "error": "Email already exists.",
                "errors": None,
                "form_data": form_data,
            },
            status_code=400,
        )

    try:
        register_user(
            db=db,
            username=username,
            email=email,
            display_name=display_name,
            password=password,
            role="user",
        )
    except ValueError as e:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "error": str(e),
                "errors": None,
                "form_data": form_data,
            },
            status_code=400,
        )

    return RedirectResponse(url="/auth/login", status_code=302)


@router.get("/login")
def login_page(
    request: Request,
    user=Depends(get_optional_user),
):
    if user is not None:
        if user.role == "admin":
            return RedirectResponse(url="/admin/dashboard", status_code=302)
        return RedirectResponse(url="/dashboard", status_code=302)

    return templates.TemplateResponse(
        request,
        "auth/login.html",
        context={
            "error": None,
            "username": "",
        },
    )


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    username_stripped = username.strip().lower()

    if not username_stripped or not password:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={
                "error": "Username and password are required.",
                "username": username_stripped,
            },
            status_code=400,
        )

    user = authenticate_user(db, username_stripped, password)
    if user is None:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={
                "error": "Invalid username or password.",
                "username": username_stripped,
            },
            status_code=401,
        )

    access_token = create_access_token(data={"sub": str(user.id)})

    if user.role == "admin":
        redirect_url = "/admin/dashboard"
    else:
        redirect_url = "/dashboard"

    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24,
        path="/",
    )
    return response


@router.get("/logout")
def logout(request: Request):
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(
        key="access_token",
        path="/",
    )
    return response


@router.post("/logout")
def logout_post(request: Request):
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(
        key="access_token",
        path="/",
    )
    return response