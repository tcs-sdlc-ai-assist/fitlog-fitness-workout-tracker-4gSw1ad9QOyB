import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from services.measurement_service import MeasurementService
from utils.dependencies import get_current_user, flash_message, get_flash_messages

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/measurements")
def list_measurements(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    service = MeasurementService(db)

    result = service.list_measurements(user_id=user.id, page=page, per_page=20)
    trends = service.get_trend_summary(user_id=user.id)

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "measurements/list.html",
        context={
            "user": user,
            "measurements": result["measurements"],
            "total": result["total"],
            "page": result["page"],
            "per_page": result["per_page"],
            "total_pages": result["total_pages"],
            "trends": trends,
            "messages": messages,
        },
    )


@router.get("/measurements/new")
def new_measurement_form(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    service = MeasurementService(db)
    existing_dates = service.get_existing_dates(user_id=user.id)

    today = date.today().isoformat()

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "measurements/form.html",
        context={
            "user": user,
            "measurement": None,
            "today": today,
            "existing_dates": existing_dates,
            "messages": messages,
        },
    )


@router.post("/measurements/new")
def create_measurement(
    request: Request,
    measurement_date: str = Form(...),
    weight: Optional[str] = Form(None),
    body_fat_pct: Optional[str] = Form(None),
    chest: Optional[str] = Form(None),
    waist: Optional[str] = Form(None),
    hips: Optional[str] = Form(None),
    biceps: Optional[str] = Form(None),
    thighs: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    service = MeasurementService(db)

    try:
        parsed_date = date.fromisoformat(measurement_date.strip())
    except (ValueError, AttributeError):
        flash_message(request, "Invalid date format.", "error")
        return RedirectResponse(url="/measurements/new", status_code=303)

    weight_val = _parse_optional_float(weight)
    body_fat_val = _parse_optional_float(body_fat_pct)
    chest_val = _parse_optional_float(chest)
    waist_val = _parse_optional_float(waist)
    hips_val = _parse_optional_float(hips)
    biceps_val = _parse_optional_float(biceps)
    thighs_val = _parse_optional_float(thighs)
    notes_val = notes.strip() if notes and notes.strip() else None

    try:
        service.create_measurement(
            user_id=user.id,
            measurement_date=parsed_date,
            weight=weight_val,
            body_fat_pct=body_fat_val,
            chest=chest_val,
            waist=waist_val,
            hips=hips_val,
            biceps=biceps_val,
            thighs=thighs_val,
            notes=notes_val,
        )
        flash_message(request, "Measurement saved successfully.", "success")
        return RedirectResponse(url="/measurements", status_code=303)
    except ValueError as e:
        flash_message(request, str(e), "error")
        return RedirectResponse(url="/measurements/new", status_code=303)


@router.get("/measurements/{measurement_id}/edit")
def edit_measurement_form(
    request: Request,
    measurement_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    service = MeasurementService(db)

    measurement = service.get_measurement(user_id=user.id, measurement_id=measurement_id)
    if measurement is None:
        flash_message(request, "Measurement not found.", "error")
        return RedirectResponse(url="/measurements", status_code=303)

    existing_dates = service.get_existing_dates(user_id=user.id)

    measurement_dict = _measurement_to_form_dict(measurement)

    messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "measurements/form.html",
        context={
            "user": user,
            "measurement": measurement_dict,
            "today": date.today().isoformat(),
            "existing_dates": existing_dates,
            "messages": messages,
        },
    )


@router.post("/measurements/{measurement_id}/edit")
def update_measurement(
    request: Request,
    measurement_id: int,
    measurement_date: str = Form(...),
    weight: Optional[str] = Form(None),
    body_fat_pct: Optional[str] = Form(None),
    chest: Optional[str] = Form(None),
    waist: Optional[str] = Form(None),
    hips: Optional[str] = Form(None),
    biceps: Optional[str] = Form(None),
    thighs: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    service = MeasurementService(db)

    existing = service.get_measurement(user_id=user.id, measurement_id=measurement_id)
    if existing is None:
        flash_message(request, "Measurement not found.", "error")
        return RedirectResponse(url="/measurements", status_code=303)

    try:
        parsed_date = date.fromisoformat(measurement_date.strip())
    except (ValueError, AttributeError):
        flash_message(request, "Invalid date format.", "error")
        return RedirectResponse(url=f"/measurements/{measurement_id}/edit", status_code=303)

    weight_val = _parse_optional_float(weight)
    body_fat_val = _parse_optional_float(body_fat_pct)
    chest_val = _parse_optional_float(chest)
    waist_val = _parse_optional_float(waist)
    hips_val = _parse_optional_float(hips)
    biceps_val = _parse_optional_float(biceps)
    thighs_val = _parse_optional_float(thighs)
    notes_val = notes.strip() if notes and notes.strip() else None

    try:
        service.update_measurement(
            user_id=user.id,
            measurement_id=measurement_id,
            measurement_date=parsed_date,
            weight=weight_val,
            body_fat_pct=body_fat_val,
            chest=chest_val,
            waist=waist_val,
            hips=hips_val,
            biceps=biceps_val,
            thighs=thighs_val,
            notes=notes_val,
        )
        flash_message(request, "Measurement updated successfully.", "success")
        return RedirectResponse(url="/measurements", status_code=303)
    except LookupError as e:
        flash_message(request, str(e), "error")
        return RedirectResponse(url="/measurements", status_code=303)
    except ValueError as e:
        flash_message(request, str(e), "error")
        return RedirectResponse(url=f"/measurements/{measurement_id}/edit", status_code=303)


@router.post("/measurements/{measurement_id}/delete")
def delete_measurement(
    request: Request,
    measurement_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    service = MeasurementService(db)

    try:
        service.delete_measurement(user_id=user.id, measurement_id=measurement_id)
        flash_message(request, "Measurement deleted successfully.", "success")
    except LookupError as e:
        flash_message(request, str(e), "error")

    return RedirectResponse(url="/measurements", status_code=303)


def _parse_optional_float(value: Optional[str]) -> Optional[float]:
    """Parse a form string value to an optional float. Returns None for empty/invalid values."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _measurement_to_form_dict(measurement) -> dict:
    """Convert a BodyMeasurement ORM object to a dict suitable for the form template."""
    return {
        "id": measurement.id,
        "measurement_date": measurement.measurement_date.isoformat() if isinstance(measurement.measurement_date, date) else str(measurement.measurement_date) if measurement.measurement_date else "",
        "weight": measurement.weight,
        "body_fat_pct": measurement.body_fat_pct,
        "chest": measurement.chest,
        "waist": measurement.waist,
        "hips": measurement.hips,
        "biceps": measurement.left_arm,
        "thighs": measurement.left_thigh,
        "notes": None,
    }