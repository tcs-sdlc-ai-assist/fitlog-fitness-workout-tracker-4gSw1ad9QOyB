import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from services.exercise_service import ExerciseService
from services.pr_service import PRService
from utils.dependencies import get_current_user, get_flash_messages

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/exercises")
def exercise_library(
    request: Request,
    search: str = Query(default=None),
    muscle_group: str = Query(default=None),
    equipment: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    exercise_service = ExerciseService(db)
    pr_service = PRService(db)

    result = exercise_service.list_exercises(
        search=search,
        muscle_group=muscle_group,
        equipment=equipment,
        page=page,
        per_page=20,
    )

    personal_records = pr_service.get_exercise_prs_map(user.id)

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "exercises/library.html",
        context={
            "user": user,
            "exercises": result["exercises"],
            "total": result["total"],
            "page": result["page"],
            "per_page": result["per_page"],
            "total_pages": result["total_pages"],
            "search": search,
            "muscle_group": muscle_group,
            "equipment": equipment,
            "personal_records": personal_records,
            "messages": messages,
        },
    )


@router.get("/exercises/{exercise_id}")
def exercise_detail(
    request: Request,
    exercise_id: int,
    page: int = Query(default=1, ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    exercise_service = ExerciseService(db)
    pr_service = PRService(db)

    exercise = exercise_service.get_exercise_by_id(exercise_id)
    if exercise is None:
        return RedirectResponse(url="/exercises", status_code=302)

    history_result = exercise_service.get_exercise_history(
        user_id=user.id,
        exercise_id=exercise_id,
        page=page,
        per_page=20,
    )

    personal_records = pr_service.get_exercise_prs(user.id, exercise_id)

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "exercises/detail.html",
        context={
            "user": user,
            "exercise": exercise,
            "history": history_result["history"],
            "total": history_result["total"],
            "page": history_result["page"],
            "per_page": history_result["per_page"],
            "total_pages": history_result["total_pages"],
            "personal_records": personal_records,
            "messages": messages,
        },
    )