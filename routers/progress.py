import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from services.progress_service import ProgressService
from utils.dependencies import get_current_user, get_flash_messages

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/progress")
def progress_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    progress_service = ProgressService(db)

    summary = progress_service.get_progress_summary(user.id)

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "progress/index.html",
        context={
            "user": user,
            "consistency": summary["consistency"],
            "muscle_group_distribution": summary["muscle_group_distribution"],
            "recent_prs": summary["recent_prs"],
            "all_prs": summary["all_prs"],
            "messages": messages,
        },
    )