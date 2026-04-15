import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import re
import calendar
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from utils.dependencies import get_current_user, get_optional_user, flash_message, get_flash_messages
from services.workout_service import (
    create_workout,
    update_workout,
    delete_workout,
    get_workout_by_id,
    list_workouts,
    get_workout_calendar_data,
    get_month_stats,
)
from services.exercise_service import ExerciseService
from services.template_service import TemplateService
from services.pr_service import PRService

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _parse_exercises_from_form(form_data: dict) -> list:
    """Parse the nested exercises[idx][field] and exercises[idx][sets][idx][field] from form data."""
    exercises_map: dict = {}

    for key, value in form_data.items():
        match = re.match(r"exercises\[(\d+)\]\[(\w+)\]", key)
        if match:
            ex_idx = int(match.group(1))
            field = match.group(2)

            if ex_idx not in exercises_map:
                exercises_map[ex_idx] = {"sets": {}}

            set_match = re.match(r"exercises\[\d+\]\[sets\]\[(\d+)\]\[(\w+)\]", key)
            if set_match:
                set_idx = int(set_match.group(1))
                set_field = set_match.group(2)
                if set_idx not in exercises_map[ex_idx]["sets"]:
                    exercises_map[ex_idx]["sets"][set_idx] = {}
                exercises_map[ex_idx]["sets"][set_idx][set_field] = value
            else:
                exercises_map[ex_idx][field] = value

    exercises = []
    for ex_idx in sorted(exercises_map.keys()):
        ex_data = exercises_map[ex_idx]
        exercise_id = ex_data.get("exercise_id")
        if not exercise_id:
            continue

        sets_map = ex_data.get("sets", {})
        sets_list = []
        for set_idx in sorted(sets_map.keys()):
            s = sets_map[set_idx]
            sets_list.append({
                "set_number": s.get("set_number", set_idx + 1),
                "weight": s.get("weight", None),
                "reps": s.get("reps", 0),
            })

        exercises.append({
            "exercise_id": exercise_id,
            "sort_order": ex_data.get("sort_order", ex_idx + 1),
            "notes": ex_data.get("notes", ""),
            "sets": sets_list,
        })

    return exercises


@router.get("/workouts")
def workouts_redirect(request: Request):
    return RedirectResponse(url="/workouts/history", status_code=302)


@router.get("/workouts/history")
def workout_history(
    request: Request,
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    page: int = Query(1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    current_year = year if year else today.year
    current_month = month if month else today.month

    if current_month < 1:
        current_month = 1
    if current_month > 12:
        current_month = 12

    month_name = calendar.month_name[current_month]

    if current_month == 1:
        prev_year = current_year - 1
        prev_month = 12
    else:
        prev_year = current_year
        prev_month = current_month - 1

    if current_month == 12:
        next_year = current_year + 1
        next_month = 1
    else:
        next_year = current_year
        next_month = current_month + 1

    calendar_days = get_workout_calendar_data(db, user.id, current_year, current_month)
    month_stats_data = get_month_stats(db, user.id, current_year, current_month)

    first_day = date(current_year, current_month, 1)
    _, last_day_num = calendar.monthrange(current_year, current_month)
    last_day = date(current_year, current_month, last_day_num)

    result = list_workouts(
        db,
        user_id=user.id,
        page=page,
        per_page=20,
        date_from=first_day,
        date_to=last_day,
    )

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "workouts/history.html",
        context={
            "user": user,
            "workouts": result["items"],
            "total": result["total"],
            "page": result["page"],
            "per_page": result["per_page"],
            "total_pages": result["total_pages"],
            "calendar_days": calendar_days,
            "month_stats": month_stats_data,
            "month_name": month_name,
            "current_year": current_year,
            "current_month": current_month,
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
            "messages": messages,
        },
    )


@router.get("/workouts/new")
def new_workout_form(
    request: Request,
    template_id: Optional[int] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exercise_service = ExerciseService(db)
    all_exercises = exercise_service.get_all_exercises()

    template_service = TemplateService(db)
    all_templates = template_service.list_all_templates_for_workout(user.id)

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "workouts/form.html",
        context={
            "user": user,
            "workout": None,
            "exercises": all_exercises,
            "templates": all_templates,
            "today": date.today().isoformat(),
            "messages": messages,
        },
    )


@router.post("/workouts/new")
async def create_new_workout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form_data = await request.form()
    form_dict = dict(form_data)

    name = form_dict.get("name", "").strip()
    workout_date_str = form_dict.get("workout_date", "")
    duration_str = form_dict.get("duration_minutes", "")
    notes = form_dict.get("notes", "")

    if not name:
        exercise_service = ExerciseService(db)
        all_exercises = exercise_service.get_all_exercises()
        template_service = TemplateService(db)
        all_templates = template_service.list_all_templates_for_workout(user.id)
        flash_message(request, "Workout name is required.", "error")
        messages = get_flash_messages(request)
        return templates.TemplateResponse(
            request,
            "workouts/form.html",
            context={
                "user": user,
                "workout": None,
                "exercises": all_exercises,
                "templates": all_templates,
                "today": date.today().isoformat(),
                "messages": messages,
            },
        )

    try:
        workout_date = date.fromisoformat(workout_date_str)
    except (ValueError, TypeError):
        workout_date = date.today()

    duration_minutes = None
    if duration_str:
        try:
            duration_minutes = int(duration_str)
        except (ValueError, TypeError):
            duration_minutes = None

    exercises = _parse_exercises_from_form(form_dict)

    if not exercises:
        exercise_service = ExerciseService(db)
        all_exercises = exercise_service.get_all_exercises()
        template_service = TemplateService(db)
        all_templates = template_service.list_all_templates_for_workout(user.id)
        flash_message(request, "At least one exercise is required.", "error")
        messages = get_flash_messages(request)
        return templates.TemplateResponse(
            request,
            "workouts/form.html",
            context={
                "user": user,
                "workout": None,
                "exercises": all_exercises,
                "templates": all_templates,
                "today": date.today().isoformat(),
                "messages": messages,
            },
        )

    try:
        workout = create_workout(
            db=db,
            user_id=user.id,
            name=name,
            workout_date=workout_date,
            duration_minutes=duration_minutes,
            notes=notes,
            exercises=exercises,
        )

        pr_service = PRService(db)
        pr_service.detect_prs_for_workout(user.id, workout.id)
        db.commit()

        template_id_str = form_dict.get("template_id", "")
        if template_id_str:
            try:
                tid = int(template_id_str)
                template_service = TemplateService(db)
                template_service.increment_usage_count(tid)
            except (ValueError, TypeError):
                pass

        flash_message(request, "Workout saved successfully!", "success")
        return RedirectResponse(url=f"/workouts/{workout.id}", status_code=302)

    except Exception as e:
        db.rollback()
        exercise_service = ExerciseService(db)
        all_exercises = exercise_service.get_all_exercises()
        template_service = TemplateService(db)
        all_templates = template_service.list_all_templates_for_workout(user.id)
        flash_message(request, f"Error saving workout: {str(e)}", "error")
        messages = get_flash_messages(request)
        return templates.TemplateResponse(
            request,
            "workouts/form.html",
            context={
                "user": user,
                "workout": None,
                "exercises": all_exercises,
                "templates": all_templates,
                "today": date.today().isoformat(),
                "messages": messages,
            },
        )


@router.get("/workouts/{workout_id}")
def workout_detail(
    request: Request,
    workout_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workout = get_workout_by_id(db, user.id, workout_id)
    if workout is None:
        flash_message(request, "Workout not found.", "error")
        return RedirectResponse(url="/workouts/history", status_code=302)

    workout_exercises = []
    total_sets = 0
    if workout.workout_exercises:
        for we in sorted(workout.workout_exercises, key=lambda x: x.sort_order):
            exercise_name = we.exercise.name if we.exercise else f"Exercise #{we.exercise_id}"
            sets_data = []
            if we.sets:
                for s in sorted(we.sets, key=lambda x: x.set_number):
                    sets_data.append({
                        "set_number": s.set_number,
                        "weight": s.weight,
                        "reps": s.reps,
                        "is_completed": s.is_completed,
                        "is_pr": s.is_pr,
                    })
                    total_sets += 1

            workout_exercises.append({
                "exercise_id": we.exercise_id,
                "exercise_name": exercise_name,
                "sort_order": we.sort_order,
                "notes": we.notes,
                "sets": sets_data,
            })

    workout_view = {
        "id": workout.id,
        "user_id": workout.user_id,
        "name": workout.name,
        "workout_date": workout.workout_date,
        "duration_minutes": workout.duration_minutes,
        "notes": workout.notes,
        "created_at": workout.created_at,
        "updated_at": workout.updated_at,
        "exercises": workout_exercises,
    }

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "workouts/detail.html",
        context={
            "user": user,
            "workout": workout_view,
            "total_sets": total_sets,
            "messages": messages,
        },
    )


@router.get("/workouts/{workout_id}/edit")
def edit_workout_form(
    request: Request,
    workout_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workout = get_workout_by_id(db, user.id, workout_id)
    if workout is None:
        flash_message(request, "Workout not found.", "error")
        return RedirectResponse(url="/workouts/history", status_code=302)

    if workout.user_id != user.id:
        flash_message(request, "You do not have permission to edit this workout.", "error")
        return RedirectResponse(url="/workouts/history", status_code=302)

    exercise_service = ExerciseService(db)
    all_exercises = exercise_service.get_all_exercises()

    workout_exercises = []
    if workout.workout_exercises:
        for we in sorted(workout.workout_exercises, key=lambda x: x.sort_order):
            sets_data = []
            if we.sets:
                for s in sorted(we.sets, key=lambda x: x.set_number):
                    sets_data.append({
                        "set_number": s.set_number,
                        "weight": s.weight,
                        "reps": s.reps,
                    })

            workout_exercises.append({
                "exercise_id": we.exercise_id,
                "sort_order": we.sort_order,
                "notes": we.notes or "",
                "sets": sets_data,
            })

    workout_view = {
        "id": workout.id,
        "user_id": workout.user_id,
        "name": workout.name,
        "workout_date": workout.workout_date,
        "duration_minutes": workout.duration_minutes,
        "notes": workout.notes or "",
        "exercises": workout_exercises,
    }

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "workouts/form.html",
        context={
            "user": user,
            "workout": workout_view,
            "exercises": all_exercises,
            "templates": [],
            "today": date.today().isoformat(),
            "messages": messages,
        },
    )


@router.post("/workouts/{workout_id}/edit")
async def update_existing_workout(
    request: Request,
    workout_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing_workout = get_workout_by_id(db, user.id, workout_id)
    if existing_workout is None:
        flash_message(request, "Workout not found.", "error")
        return RedirectResponse(url="/workouts/history", status_code=302)

    if existing_workout.user_id != user.id:
        flash_message(request, "You do not have permission to edit this workout.", "error")
        return RedirectResponse(url="/workouts/history", status_code=302)

    form_data = await request.form()
    form_dict = dict(form_data)

    name = form_dict.get("name", "").strip()
    workout_date_str = form_dict.get("workout_date", "")
    duration_str = form_dict.get("duration_minutes", "")
    notes = form_dict.get("notes", "")

    if not name:
        exercise_service = ExerciseService(db)
        all_exercises = exercise_service.get_all_exercises()
        flash_message(request, "Workout name is required.", "error")
        messages = get_flash_messages(request)

        workout_view = {
            "id": existing_workout.id,
            "user_id": existing_workout.user_id,
            "name": existing_workout.name,
            "workout_date": existing_workout.workout_date,
            "duration_minutes": existing_workout.duration_minutes,
            "notes": existing_workout.notes or "",
            "exercises": [],
        }

        return templates.TemplateResponse(
            request,
            "workouts/form.html",
            context={
                "user": user,
                "workout": workout_view,
                "exercises": all_exercises,
                "templates": [],
                "today": date.today().isoformat(),
                "messages": messages,
            },
        )

    try:
        workout_date = date.fromisoformat(workout_date_str)
    except (ValueError, TypeError):
        workout_date = existing_workout.workout_date

    duration_minutes = None
    if duration_str:
        try:
            duration_minutes = int(duration_str)
        except (ValueError, TypeError):
            duration_minutes = None

    exercises = _parse_exercises_from_form(form_dict)

    if not exercises:
        exercise_service = ExerciseService(db)
        all_exercises = exercise_service.get_all_exercises()
        flash_message(request, "At least one exercise is required.", "error")
        messages = get_flash_messages(request)

        workout_view = {
            "id": existing_workout.id,
            "user_id": existing_workout.user_id,
            "name": name or existing_workout.name,
            "workout_date": workout_date or existing_workout.workout_date,
            "duration_minutes": duration_minutes,
            "notes": notes or existing_workout.notes or "",
            "exercises": [],
        }

        return templates.TemplateResponse(
            request,
            "workouts/form.html",
            context={
                "user": user,
                "workout": workout_view,
                "exercises": all_exercises,
                "templates": [],
                "today": date.today().isoformat(),
                "messages": messages,
            },
        )

    try:
        updated_workout = update_workout(
            db=db,
            user_id=user.id,
            workout_id=workout_id,
            name=name,
            workout_date=workout_date,
            duration_minutes=duration_minutes,
            notes=notes,
            exercises=exercises,
        )

        if updated_workout is None:
            flash_message(request, "Workout not found.", "error")
            return RedirectResponse(url="/workouts/history", status_code=302)

        pr_service = PRService(db)
        pr_service.detect_prs_for_workout(user.id, updated_workout.id)
        db.commit()

        flash_message(request, "Workout updated successfully!", "success")
        return RedirectResponse(url=f"/workouts/{workout_id}", status_code=302)

    except Exception as e:
        db.rollback()
        exercise_service = ExerciseService(db)
        all_exercises = exercise_service.get_all_exercises()
        flash_message(request, f"Error updating workout: {str(e)}", "error")
        messages = get_flash_messages(request)

        workout_view = {
            "id": existing_workout.id,
            "user_id": existing_workout.user_id,
            "name": name or existing_workout.name,
            "workout_date": workout_date or existing_workout.workout_date,
            "duration_minutes": duration_minutes,
            "notes": notes or existing_workout.notes or "",
            "exercises": [],
        }

        return templates.TemplateResponse(
            request,
            "workouts/form.html",
            context={
                "user": user,
                "workout": workout_view,
                "exercises": all_exercises,
                "templates": [],
                "today": date.today().isoformat(),
                "messages": messages,
            },
        )


@router.post("/workouts/{workout_id}/delete")
def delete_existing_workout(
    request: Request,
    workout_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing_workout = get_workout_by_id(db, user.id, workout_id)
    if existing_workout is None:
        flash_message(request, "Workout not found.", "error")
        return RedirectResponse(url="/workouts/history", status_code=302)

    if existing_workout.user_id != user.id:
        flash_message(request, "You do not have permission to delete this workout.", "error")
        return RedirectResponse(url="/workouts/history", status_code=302)

    try:
        deleted = delete_workout(db, user.id, workout_id)
        if deleted:
            flash_message(request, "Workout deleted successfully.", "success")
        else:
            flash_message(request, "Could not delete workout.", "error")
    except Exception as e:
        db.rollback()
        flash_message(request, f"Error deleting workout: {str(e)}", "error")

    return RedirectResponse(url="/workouts/history", status_code=302)