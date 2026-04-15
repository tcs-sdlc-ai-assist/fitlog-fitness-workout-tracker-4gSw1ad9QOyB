import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Optional, Generator

from fastapi import Request, HTTPException, status, Depends

from database import SessionLocal, get_db
from models.user import User
from utils.security import verify_token


def get_db_session() -> Generator:
    """Yield a SQLAlchemy database session, closing it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_from_cookie(request: Request) -> Optional[dict]:
    """Extract and validate JWT token from HTTP-only cookie.
    
    Returns the decoded payload dict or None if no valid token.
    """
    token = request.cookies.get("access_token")
    if not token:
        return None

    if token.startswith("Bearer "):
        token = token[7:]

    payload = verify_token(token)
    return payload


def get_current_user(
    request: Request,
    db=Depends(get_db),
) -> User:
    """Dependency that extracts the current authenticated user from the JWT cookie.
    
    Raises 401 if no valid token or user not found.
    """
    payload = get_current_user_from_cookie(request)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def get_optional_user(
    request: Request,
    db=Depends(get_db),
) -> Optional[User]:
    """Dependency that returns the current user if authenticated, or None otherwise.
    
    Does not raise exceptions for unauthenticated requests.
    """
    payload = get_current_user_from_cookie(request)
    if payload is None:
        return None

    user_id_str = payload.get("sub")
    if user_id_str is None:
        return None

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        return None

    user = db.query(User).filter(User.id == user_id).first()
    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency that ensures the current user has admin role.
    
    Raises 403 if the user is not an admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def template_context(
    request: Request,
    user: Optional[User] = None,
    **kwargs,
) -> dict:
    """Build a template context dict with common variables.
    
    Injects the current user and request into the context for Jinja2 templates.
    """
    context = {
        "user": user,
        **kwargs,
    }
    return context


def flash_message(request: Request, message: str, msg_type: str = "info") -> None:
    """Store a flash message in the request state for display in templates.
    
    Messages are stored as a list of dicts with 'text' and 'type' keys.
    """
    if not hasattr(request.state, "messages"):
        request.state.messages = []
    request.state.messages.append({"text": message, "type": msg_type})


def get_flash_messages(request: Request) -> list:
    """Retrieve and clear flash messages from request state."""
    messages = getattr(request.state, "messages", [])
    if hasattr(request.state, "messages"):
        request.state.messages = []
    return messages