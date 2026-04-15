import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from services.template_service import TemplateService
from services.exercise_service import ExerciseService
from utils.dependencies import get_current_user, flash_message, get_flash_messages

router = APIRouter()

templates_dir = str(Path(__file__).resolve().parent.parent / "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/templates")
def list_templates(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template_service = TemplateService(db)
    result = template_service.list_templates(user.id)

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "templates_dir/list.html",
        context={
            "user": user,
            "user_templates": result["user_templates"],
            "system_templates": result["system_templates"],
            "messages": messages,
        },
    )


@router.get("/templates/new")
def new_template_form(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    exercise_service = ExerciseService(db)
    all_exercises = exercise_service.get_all_exercises()

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "templates_dir/form.html",
        context={
            "user": user,
            "template": None,
            "exercises": all_exercises,
            "error": None,
            "messages": messages,
        },
    )


@router.post("/templates/new")
def create_template(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template_service = TemplateService(db)
    exercise_service = ExerciseService(db)

    exercises_data = _parse_template_exercises_from_form(request)

    try:
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

        template = template_service.create_template(
            user_id=user.id,
            name=name.strip(),
            description=description.strip() if description else None,
            is_system=False,
            exercises=exercises_list,
        )

        flash_message(request, "Template created successfully!", "success")
        return RedirectResponse(url=f"/templates/{template.id}", status_code=303)

    except (ValueError, Exception) as e:
        all_exercises = exercise_service.get_all_exercises()
        messages = get_flash_messages(request)

        return templates.TemplateResponse(
            request,
            "templates_dir/form.html",
            context={
                "user": user,
                "template": None,
                "exercises": all_exercises,
                "error": str(e),
                "messages": messages,
            },
            status_code=400,
        )


@router.get("/templates/{template_id}")
def template_detail(
    request: Request,
    template_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template_service = TemplateService(db)
    template = template_service.get_template_by_id(template_id)

    if template is None:
        flash_message(request, "Template not found.", "error")
        return RedirectResponse(url="/templates", status_code=303)

    is_owner = (template.user_id is not None and template.user_id == user.id)

    if not template.is_system and not is_owner and user.role != "admin":
        flash_message(request, "You don't have permission to view this template.", "error")
        return RedirectResponse(url="/templates", status_code=303)

    exercise_list = []
    if template.template_exercises:
        for te in sorted(template.template_exercises, key=lambda x: x.sort_order):
            exercise_name = te.exercise.name if te.exercise else f"Exercise #{te.exercise_id}"
            exercise_list.append({
                "id": te.id,
                "template_id": te.template_id,
                "exercise_id": te.exercise_id,
                "exercise_name": exercise_name,
                "sort_order": te.sort_order,
                "default_sets": te.default_sets,
                "default_reps": te.default_reps,
                "default_weight": te.default_weight,
                "notes": te.notes,
            })

    class TemplateView:
        pass

    tv = TemplateView()
    tv.id = template.id
    tv.user_id = template.user_id
    tv.name = template.name
    tv.description = template.description
    tv.is_system = template.is_system
    tv.usage_count = template.usage_count or 0
    tv.created_at = template.created_at
    tv.updated_at = template.updated_at
    tv.exercises = exercise_list

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "templates_dir/detail.html",
        context={
            "user": user,
            "template": tv,
            "is_owner": is_owner,
            "messages": messages,
        },
    )


@router.get("/templates/{template_id}/edit")
def edit_template_form(
    request: Request,
    template_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template_service = TemplateService(db)
    exercise_service = ExerciseService(db)

    template = template_service.get_template_by_id(template_id)

    if template is None:
        flash_message(request, "Template not found.", "error")
        return RedirectResponse(url="/templates", status_code=303)

    is_owner = (template.user_id is not None and template.user_id == user.id)
    is_admin = user.role == "admin"

    if not is_owner and not (is_admin and template.is_system):
        flash_message(request, "You don't have permission to edit this template.", "error")
        return RedirectResponse(url="/templates", status_code=303)

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
def update_template(
    request: Request,
    template_id: int,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template_service = TemplateService(db)
    exercise_service = ExerciseService(db)

    template = template_service.get_template_by_id(template_id)

    if template is None:
        flash_message(request, "Template not found.", "error")
        return RedirectResponse(url="/templates", status_code=303)

    is_owner = (template.user_id is not None and template.user_id == user.id)
    is_admin = user.role == "admin"

    if not is_owner and not (is_admin and template.is_system):
        flash_message(request, "You don't have permission to edit this template.", "error")
        return RedirectResponse(url="/templates", status_code=303)

    exercises_data = _parse_template_exercises_from_form(request)

    try:
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

        if is_owner:
            updated = template_service.update_template(
                template_id=template_id,
                user_id=user.id,
                name=name.strip(),
                description=description.strip() if description else None,
                exercises=exercises_list,
            )
        elif is_admin and template.is_system:
            template.name = name.strip()
            template.description = description.strip() if description else None

            for te in list(template.template_exercises):
                db.delete(te)
            db.flush()

            from models.template_exercise import TemplateExercise
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
            updated = template
        else:
            updated = None

        if updated is None:
            flash_message(request, "Failed to update template.", "error")
            return RedirectResponse(url="/templates", status_code=303)

        flash_message(request, "Template updated successfully!", "success")
        return RedirectResponse(url=f"/templates/{template_id}", status_code=303)

    except (ValueError, Exception) as e:
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
        tev.is_system = template.is_system if template else False
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
def delete_template(
    request: Request,
    template_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template_service = TemplateService(db)
    template = template_service.get_template_by_id(template_id)

    if template is None:
        flash_message(request, "Template not found.", "error")
        return RedirectResponse(url="/templates", status_code=303)

    is_owner = (template.user_id is not None and template.user_id == user.id)
    is_admin = user.role == "admin"

    if is_owner:
        deleted = template_service.delete_template(template_id, user.id)
    elif is_admin:
        deleted = template_service.delete_template(template_id, user.id, is_admin=True)
    else:
        flash_message(request, "You don't have permission to delete this template.", "error")
        return RedirectResponse(url="/templates", status_code=303)

    if deleted:
        flash_message(request, "Template deleted successfully.", "success")
    else:
        flash_message(request, "Failed to delete template.", "error")

    return RedirectResponse(url="/templates", status_code=303)


@router.post("/templates/{template_id}/clone")
def clone_template(
    request: Request,
    template_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template_service = TemplateService(db)

    source = template_service.get_template_by_id(template_id)
    if source is None:
        flash_message(request, "Template not found.", "error")
        return RedirectResponse(url="/templates", status_code=303)

    cloned = template_service.clone_template(template_id, user.id)

    if cloned is None:
        flash_message(request, "Failed to clone template.", "error")
        return RedirectResponse(url="/templates", status_code=303)

    flash_message(request, f"Template '{source.name}' cloned to your templates!", "success")
    return RedirectResponse(url=f"/templates/{cloned.id}", status_code=303)


@router.get("/api/templates/{template_id}")
def api_get_template(
    request: Request,
    template_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template_service = TemplateService(db)
    data = template_service.get_template_for_api(template_id)

    if data is None:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Template not found"})

    template = template_service.get_template_by_id(template_id)
    if template and not template.is_system:
        if template.user_id != user.id and user.role != "admin":
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=403, content={"error": "Access denied"})

    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=200, content=data)


def _parse_template_exercises_from_form(request: Request) -> list:
    form_data = {}
    if hasattr(request, "_form"):
        form_data = request._form
    else:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    form_data = pool.submit(lambda: asyncio.run(_get_form(request))).result()
            else:
                form_data = loop.run_until_complete(request.form())
        except RuntimeError:
            form_data = asyncio.run(_get_form(request))

    exercises = {}

    for key in form_data:
        value = form_data[key]
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


async def _get_form(request: Request):
    return await request.form()