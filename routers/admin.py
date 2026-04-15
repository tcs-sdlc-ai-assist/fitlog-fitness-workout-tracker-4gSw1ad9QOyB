import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models.user import User
from services.dashboard_service import DashboardService
from services.exercise_service import ExerciseService
from services.template_service import TemplateService
from services.auth_service import get_user_by_id, delete_user
from utils.dependencies import require_admin, get_flash_messages, flash_message

router = APIRouter(prefix="/admin", tags=["admin"])

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/dashboard")
def admin_dashboard(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    dashboard_service = DashboardService(db)
    data = dashboard_service.get_admin_dashboard_data()

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        context={
            "user": user,
            "stats": data["stats"],
            "users": data["users"],
            "exercises": data["exercises"],
            "system_templates": data["system_templates"],
            "messages": messages,
        },
    )


@router.post("/exercises")
def create_exercise(
    request: Request,
    name: str = Form(...),
    muscle_group: str = Form(...),
    equipment: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    exercise_service = ExerciseService(db)

    name = name.strip()
    muscle_group = muscle_group.strip()
    equipment_val = equipment.strip() if equipment and equipment.strip() else None
    instructions_val = instructions.strip() if instructions and instructions.strip() else None

    if not name:
        flash_message(request, "Exercise name is required.", "error")
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    if not muscle_group:
        flash_message(request, "Muscle group is required.", "error")
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    try:
        exercise_service.create_exercise(
            name=name,
            muscle_group=muscle_group,
            equipment=equipment_val,
            instructions=instructions_val,
            is_system=True,
        )
        flash_message(request, f"Exercise '{name}' created successfully.", "success")
    except ValueError as e:
        flash_message(request, str(e), "error")

    return RedirectResponse(url="/admin/dashboard", status_code=303)


@router.get("/exercises/{exercise_id}/edit")
def edit_exercise_form(
    request: Request,
    exercise_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    exercise_service = ExerciseService(db)
    exercise = exercise_service.get_exercise_by_id(exercise_id)

    if exercise is None:
        flash_message(request, "Exercise not found.", "error")
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "admin/edit_exercise.html",
        context={
            "user": user,
            "exercise": exercise,
            "error": None,
            "messages": messages,
        },
    )


@router.post("/exercises/{exercise_id}/edit")
def update_exercise(
    request: Request,
    exercise_id: int,
    name: str = Form(...),
    muscle_group: str = Form(...),
    equipment: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    exercise_service = ExerciseService(db)

    name = name.strip()
    muscle_group = muscle_group.strip()
    equipment_val = equipment.strip() if equipment and equipment.strip() else None
    instructions_val = instructions.strip() if instructions and instructions.strip() else None

    if not name:
        flash_message(request, "Exercise name is required.", "error")
        return RedirectResponse(url=f"/admin/exercises/{exercise_id}/edit", status_code=303)

    if not muscle_group:
        flash_message(request, "Muscle group is required.", "error")
        return RedirectResponse(url=f"/admin/exercises/{exercise_id}/edit", status_code=303)

    try:
        updated = exercise_service.update_exercise(
            exercise_id=exercise_id,
            name=name,
            muscle_group=muscle_group,
            equipment=equipment_val,
            instructions=instructions_val,
        )
        if updated is None:
            flash_message(request, "Exercise not found.", "error")
        else:
            flash_message(request, f"Exercise '{name}' updated successfully.", "success")
    except ValueError as e:
        flash_message(request, str(e), "error")
        return RedirectResponse(url=f"/admin/exercises/{exercise_id}/edit", status_code=303)

    return RedirectResponse(url="/admin/dashboard", status_code=303)


@router.post("/exercises/{exercise_id}/delete")
def delete_exercise(
    request: Request,
    exercise_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    exercise_service = ExerciseService(db)

    exercise = exercise_service.get_exercise_by_id(exercise_id)
    if exercise is None:
        flash_message(request, "Exercise not found.", "error")
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    exercise_name = exercise.name

    try:
        deleted = exercise_service.delete_exercise(exercise_id)
        if deleted:
            flash_message(request, f"Exercise '{exercise_name}' deleted successfully.", "success")
        else:
            flash_message(request, "Failed to delete exercise.", "error")
    except Exception as e:
        flash_message(request, f"Error deleting exercise: {str(e)}", "error")

    return RedirectResponse(url="/admin/dashboard", status_code=303)


@router.post("/templates")
def create_system_template(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    is_system: Optional[str] = Form(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    template_service = TemplateService(db)

    name = name.strip()
    description_val = description.strip() if description and description.strip() else None

    if not name:
        flash_message(request, "Template name is required.", "error")
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    try:
        template_service.create_template(
            user_id=user.id,
            name=name,
            description=description_val,
            is_system=True,
            exercises=[],
        )
        flash_message(request, f"System template '{name}' created successfully.", "success")
    except (ValueError, Exception) as e:
        flash_message(request, str(e), "error")

    return RedirectResponse(url="/admin/dashboard", status_code=303)


@router.get("/templates/{template_id}/edit")
def edit_template_form(
    request: Request,
    template_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    template_service = TemplateService(db)
    exercise_service = ExerciseService(db)

    template = template_service.get_template_by_id(template_id)

    if template is None:
        flash_message(request, "Template not found.", "error")
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    all_exercises = exercise_service.get_all_exercises()

    template_exercises = []
    if template.template_exercises:
        for te in sorted(template.template_exercises, key=lambda x: x.sort_order):
            template_exercises.append({
                "exercise_id": te.exercise_id,
                "sort_order": te.sort_order,
                "default_sets": te.default_sets,
                "default_reps": te.default_reps,
                "default_weight": te.default_weight,
                "notes": te.notes,
            })

    class TemplateEditView:
        pass

    tev = TemplateEditView()
    tev.id = template.id
    tev.name = template.name
    tev.description = template.description
    tev.is_system = template.is_system
    tev.exercises = template_exercises

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "templates_dir/form.html",
        context={
            "user": user,
            "template": tev,
            "exercises": all_exercises,
            "error": None,
            "messages": messages,
        },
    )


@router.post("/templates/{template_id}/edit")
async def update_system_template(
    request: Request,
    template_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    template_service = TemplateService(db)
    exercise_service = ExerciseService(db)

    template = template_service.get_template_by_id(template_id)

    if template is None:
        flash_message(request, "Template not found.", "error")
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    form_data = await request.form()
    form_dict = dict(form_data)

    name = form_dict.get("name", "").strip()
    description = form_dict.get("description", "").strip() or None

    if not name:
        flash_message(request, "Template name is required.", "error")
        return RedirectResponse(url=f"/admin/templates/{template_id}/edit", status_code=303)

    exercises_data = _parse_template_exercises_from_form_dict(form_dict)

    try:
        from models.template_exercise import TemplateExercise

        template.name = name
        template.description = description

        for te in list(template.template_exercises):
            db.delete(te)
        db.flush()

        exercises_list = []
        for ex_data in exercises_data:
            exercises_list.append({
                "exercise_id": ex_data["exercise_id"],
                "sort_order": ex_data.get("sort_order", 1),
                "default_sets": ex_data.get("default_sets", 3),
                "default_reps": ex_data.get("default_reps", 10),
                "default_weight": ex_data.get("default_weight"),
                "notes": ex_data.get("notes"),
            })

        for idx, ex_data in enumerate(exercises_list):
            te = TemplateExercise(
                template_id=template.id,
                exercise_id=int(ex_data["exercise_id"]),
                sort_order=int(ex_data.get("sort_order", idx + 1)),
                default_sets=int(ex_data.get("default_sets", 3)),
                default_reps=int(ex_data.get("default_reps", 10)),
                default_weight=float(ex_data["default_weight"]) if ex_data.get("default_weight") else None,
                notes=ex_data.get("notes"),
            )
            db.add(te)

        db.commit()
        db.refresh(template)

        flash_message(request, f"Template '{name}' updated successfully.", "success")
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    except (ValueError, Exception) as e:
        db.rollback()
        all_exercises = exercise_service.get_all_exercises()

        template_exercises = []
        for ex_data in exercises_data:
            template_exercises.append({
                "exercise_id": ex_data.get("exercise_id"),
                "sort_order": ex_data.get("sort_order", 1),
                "default_sets": ex_data.get("default_sets", 3),
                "default_reps": ex_data.get("default_reps", 10),
                "default_weight": ex_data.get("default_weight"),
                "notes": ex_data.get("notes"),
            })

        class TemplateEditView:
            pass

        tev = TemplateEditView()
        tev.id = template_id
        tev.name = name
        tev.description = description
        tev.is_system = template.is_system if template else True
        tev.exercises = template_exercises

        messages = get_flash_messages(request)

        return templates.TemplateResponse(
            request,
            "templates_dir/form.html",
            context={
                "user": user,
                "template": tev,
                "exercises": all_exercises,
                "error": str(e),
                "messages": messages,
            },
            status_code=400,
        )


@router.post("/templates/{template_id}/delete")
def delete_system_template(
    request: Request,
    template_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    template_service = TemplateService(db)

    template = template_service.get_template_by_id(template_id)
    if template is None:
        flash_message(request, "Template not found.", "error")
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    template_name = template.name

    try:
        deleted = template_service.delete_template(template_id, user.id, is_admin=True)
        if deleted:
            flash_message(request, f"Template '{template_name}' deleted successfully.", "success")
        else:
            flash_message(request, "Failed to delete template.", "error")
    except Exception as e:
        flash_message(request, f"Error deleting template: {str(e)}", "error")

    return RedirectResponse(url="/admin/dashboard", status_code=303)


@router.post("/users/{user_id}/delete")
def delete_user_account(
    request: Request,
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    if user_id == user.id:
        flash_message(request, "You cannot delete your own account.", "error")
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    target_user = get_user_by_id(db, user_id)
    if target_user is None:
        flash_message(request, "User not found.", "error")
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    target_username = target_user.username

    try:
        delete_user(db, user_id)
        flash_message(request, f"User '{target_username}' deleted successfully.", "success")
    except ValueError as e:
        flash_message(request, str(e), "error")
    except Exception as e:
        flash_message(request, f"Error deleting user: {str(e)}", "error")

    return RedirectResponse(url="/admin/dashboard", status_code=303)


def _parse_template_exercises_from_form_dict(form_dict: dict) -> list:
    exercises = {}

    for key in form_dict:
        value = form_dict[key]
        if not key.startswith("exercises["):
            continue

        parts = key.replace("]", "").split("[")
        if len(parts) < 3:
            continue

        try:
            ex_idx = int(parts[1])
        except (ValueError, IndexError):
            continue

        field_name = parts[2]

        if ex_idx not in exercises:
            exercises[ex_idx] = {}

        if field_name == "exercise_id" and value:
            try:
                exercises[ex_idx]["exercise_id"] = int(value)
            except (ValueError, TypeError):
                pass
        elif field_name == "sort_order" and value:
            try:
                exercises[ex_idx]["sort_order"] = int(value)
            except (ValueError, TypeError):
                exercises[ex_idx]["sort_order"] = 1
        elif field_name == "default_sets" and value:
            try:
                exercises[ex_idx]["default_sets"] = int(value)
            except (ValueError, TypeError):
                exercises[ex_idx]["default_sets"] = 3
        elif field_name == "default_reps" and value:
            try:
                exercises[ex_idx]["default_reps"] = int(value)
            except (ValueError, TypeError):
                exercises[ex_idx]["default_reps"] = 10
        elif field_name == "default_weight":
            if value and str(value).strip():
                try:
                    exercises[ex_idx]["default_weight"] = float(value)
                except (ValueError, TypeError):
                    exercises[ex_idx]["default_weight"] = None
            else:
                exercises[ex_idx]["default_weight"] = None
        elif field_name == "notes":
            exercises[ex_idx]["notes"] = str(value) if value else None

    result = []
    for idx in sorted(exercises.keys()):
        ex = exercises[idx]
        if "exercise_id" in ex and ex["exercise_id"]:
            result.append(ex)

    return result