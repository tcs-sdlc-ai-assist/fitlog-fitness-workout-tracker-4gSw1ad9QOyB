import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from services.dashboard_service import DashboardService
from utils.dependencies import get_current_user, get_flash_messages

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/dashboard")
def dashboard(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    dashboard_service = DashboardService(db)
    data = dashboard_service.get_user_dashboard_data(user.id)

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        context={
            "user": user,
            "display_name": data["display_name"],
            "workouts_this_week": data["workouts_this_week"],
            "current_streak": data["current_streak"],
            "total_workouts": data["total_workouts"],
            "latest_weight": data["latest_weight"],
            "weekly_activity": data["weekly_activity"],
            "recent_workouts": data["recent_workouts"],
            "personal_records": data["personal_records"],
            "messages": messages,
        },
    )