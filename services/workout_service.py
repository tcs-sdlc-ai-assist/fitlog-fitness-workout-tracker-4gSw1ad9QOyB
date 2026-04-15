import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import calendar
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select, and_, extract
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models.workout import Workout
from models.workout_exercise import WorkoutExercise
from models.exercise_set import ExerciseSet
from models.exercise import Exercise


def create_workout(
    db: Session,
    user_id: int,
    name: str,
    workout_date: date,
    duration_minutes: Optional[int],
    notes: Optional[str],
    exercises: list[dict],
) -> Workout:
    workout = Workout(
        user_id=user_id,
        name=name.strip(),
        workout_date=workout_date,
        duration_minutes=duration_minutes,
        notes=notes or "",
    )
    db.add(workout)
    db.flush()

    for ex_data in exercises:
        workout_exercise = WorkoutExercise(
            workout_id=workout.id,
            exercise_id=int(ex_data["exercise_id"]),
            sort_order=int(ex_data.get("sort_order", 1)),
            notes=ex_data.get("notes", "") or "",
        )
        db.add(workout_exercise)
        db.flush()

        sets_data = ex_data.get("sets", [])
        for set_data in sets_data:
            weight_val = set_data.get("weight")
            if weight_val is not None and weight_val != "":
                try:
                    weight_val = float(weight_val)
                except (ValueError, TypeError):
                    weight_val = None
            else:
                weight_val = None

            reps_val = set_data.get("reps", 0)
            try:
                reps_val = int(reps_val)
            except (ValueError, TypeError):
                reps_val = 0

            exercise_set = ExerciseSet(
                workout_exercise_id=workout_exercise.id,
                set_number=int(set_data.get("set_number", 1)),
                weight=weight_val,
                reps=reps_val,
                is_completed=True,
                is_pr=False,
            )
            db.add(exercise_set)

    db.commit()
    db.refresh(workout)
    return workout


def update_workout(
    db: Session,
    user_id: int,
    workout_id: int,
    name: Optional[str] = None,
    workout_date: Optional[date] = None,
    duration_minutes: Optional[int] = None,
    notes: Optional[str] = None,
    exercises: Optional[list[dict]] = None,
) -> Optional[Workout]:
    workout = get_workout_by_id(db, user_id, workout_id)
    if workout is None:
        return None

    if name is not None:
        workout.name = name.strip()
    if workout_date is not None:
        workout.workout_date = workout_date
    if duration_minutes is not None:
        workout.duration_minutes = duration_minutes
    if notes is not None:
        workout.notes = notes

    if exercises is not None:
        for we in list(workout.workout_exercises):
            for s in list(we.sets):
                db.delete(s)
            db.delete(we)
        db.flush()

        for ex_data in exercises:
            workout_exercise = WorkoutExercise(
                workout_id=workout.id,
                exercise_id=int(ex_data["exercise_id"]),
                sort_order=int(ex_data.get("sort_order", 1)),
                notes=ex_data.get("notes", "") or "",
            )
            db.add(workout_exercise)
            db.flush()

            sets_data = ex_data.get("sets", [])
            for set_data in sets_data:
                weight_val = set_data.get("weight")
                if weight_val is not None and weight_val != "":
                    try:
                        weight_val = float(weight_val)
                    except (ValueError, TypeError):
                        weight_val = None
                else:
                    weight_val = None

                reps_val = set_data.get("reps", 0)
                try:
                    reps_val = int(reps_val)
                except (ValueError, TypeError):
                    reps_val = 0

                exercise_set = ExerciseSet(
                    workout_exercise_id=workout_exercise.id,
                    set_number=int(set_data.get("set_number", 1)),
                    weight=weight_val,
                    reps=reps_val,
                    is_completed=True,
                    is_pr=False,
                )
                db.add(exercise_set)

    db.commit()
    db.refresh(workout)
    return workout


def delete_workout(db: Session, user_id: int, workout_id: int) -> bool:
    workout = get_workout_by_id(db, user_id, workout_id)
    if workout is None:
        return False

    db.delete(workout)
    db.commit()
    return True


def get_workout_by_id(db: Session, user_id: int, workout_id: int) -> Optional[Workout]:
    stmt = (
        select(Workout)
        .where(and_(Workout.id == workout_id, Workout.user_id == user_id))
        .options(
            selectinload(Workout.workout_exercises)
            .selectinload(WorkoutExercise.sets),
            selectinload(Workout.workout_exercises)
            .selectinload(WorkoutExercise.exercise),
        )
    )
    result = db.execute(stmt)
    return result.scalar_one_or_none()


def list_workouts(
    db: Session,
    user_id: int,
    page: int = 1,
    per_page: int = 20,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 20
    if per_page > 100:
        per_page = 100

    conditions = [Workout.user_id == user_id]
    if date_from is not None:
        conditions.append(Workout.workout_date >= date_from)
    if date_to is not None:
        conditions.append(Workout.workout_date <= date_to)

    count_stmt = select(func.count(Workout.id)).where(and_(*conditions))
    total = db.execute(count_stmt).scalar() or 0

    total_pages = max(1, (total + per_page - 1) // per_page)

    offset = (page - 1) * per_page
    stmt = (
        select(Workout)
        .where(and_(*conditions))
        .order_by(Workout.workout_date.desc(), Workout.id.desc())
        .offset(offset)
        .limit(per_page)
        .options(
            selectinload(Workout.workout_exercises)
            .selectinload(WorkoutExercise.sets),
            selectinload(Workout.workout_exercises)
            .selectinload(WorkoutExercise.exercise),
        )
    )
    result = db.execute(stmt)
    workouts = result.scalars().all()

    items = []
    for w in workouts:
        exercise_count = len(w.workout_exercises) if w.workout_exercises else 0
        total_sets = 0
        if w.workout_exercises:
            for we in w.workout_exercises:
                if we.sets:
                    total_sets += len(we.sets)

        items.append({
            "id": w.id,
            "user_id": w.user_id,
            "name": w.name,
            "workout_date": w.workout_date,
            "duration_minutes": w.duration_minutes,
            "notes": w.notes,
            "created_at": w.created_at,
            "updated_at": w.updated_at,
            "exercise_count": exercise_count,
            "total_sets": total_sets,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


def get_workouts_by_date(db: Session, user_id: int, target_date: date) -> list[Workout]:
    stmt = (
        select(Workout)
        .where(and_(Workout.user_id == user_id, Workout.workout_date == target_date))
        .order_by(Workout.id.desc())
        .options(
            selectinload(Workout.workout_exercises)
            .selectinload(WorkoutExercise.sets),
            selectinload(Workout.workout_exercises)
            .selectinload(WorkoutExercise.exercise),
        )
    )
    result = db.execute(stmt)
    return list(result.scalars().all())


def get_workout_dates_for_range(
    db: Session,
    user_id: int,
    start_date: date,
    end_date: date,
) -> set[date]:
    stmt = (
        select(Workout.workout_date)
        .where(
            and_(
                Workout.user_id == user_id,
                Workout.workout_date >= start_date,
                Workout.workout_date <= end_date,
            )
        )
        .distinct()
    )
    result = db.execute(stmt)
    return {row[0] for row in result.all()}


def get_workout_calendar_data(
    db: Session,
    user_id: int,
    year: int,
    month: int,
) -> list[dict]:
    first_day = date(year, month, 1)
    _, last_day_num = calendar.monthrange(year, month)
    last_day = date(year, month, last_day_num)

    workout_dates = get_workout_dates_for_range(db, user_id, first_day, last_day)

    today = date.today()

    first_weekday = first_day.weekday()

    calendar_days = []
    for _ in range(first_weekday):
        calendar_days.append({"day": 0, "has_workout": False, "is_today": False})

    for day_num in range(1, last_day_num + 1):
        current_date = date(year, month, day_num)
        calendar_days.append({
            "day": day_num,
            "has_workout": current_date in workout_dates,
            "is_today": current_date == today,
        })

    remaining = (7 - len(calendar_days) % 7) % 7
    for _ in range(remaining):
        calendar_days.append({"day": 0, "has_workout": False, "is_today": False})

    return calendar_days


def get_month_stats(
    db: Session,
    user_id: int,
    year: int,
    month: int,
) -> dict:
    first_day = date(year, month, 1)
    _, last_day_num = calendar.monthrange(year, month)
    last_day = date(year, month, last_day_num)

    conditions = and_(
        Workout.user_id == user_id,
        Workout.workout_date >= first_day,
        Workout.workout_date <= last_day,
    )

    total_workouts_stmt = select(func.count(Workout.id)).where(conditions)
    total_workouts = db.execute(total_workouts_stmt).scalar() or 0

    workout_ids_stmt = select(Workout.id).where(conditions)
    workout_ids_result = db.execute(workout_ids_stmt)
    workout_ids = [row[0] for row in workout_ids_result.all()]

    total_exercises = 0
    total_sets = 0

    if workout_ids:
        exercise_count_stmt = (
            select(func.count(WorkoutExercise.id))
            .where(WorkoutExercise.workout_id.in_(workout_ids))
        )
        total_exercises = db.execute(exercise_count_stmt).scalar() or 0

        we_ids_stmt = (
            select(WorkoutExercise.id)
            .where(WorkoutExercise.workout_id.in_(workout_ids))
        )
        we_ids_result = db.execute(we_ids_stmt)
        we_ids = [row[0] for row in we_ids_result.all()]

        if we_ids:
            sets_count_stmt = (
                select(func.count(ExerciseSet.id))
                .where(ExerciseSet.workout_exercise_id.in_(we_ids))
            )
            total_sets = db.execute(sets_count_stmt).scalar() or 0

    return {
        "total_workouts": total_workouts,
        "total_exercises": total_exercises,
        "total_sets": total_sets,
    }


def get_recent_workouts(db: Session, user_id: int, limit: int = 5) -> list[dict]:
    stmt = (
        select(Workout)
        .where(Workout.user_id == user_id)
        .order_by(Workout.workout_date.desc(), Workout.id.desc())
        .limit(limit)
        .options(
            selectinload(Workout.workout_exercises)
            .selectinload(WorkoutExercise.sets),
        )
    )
    result = db.execute(stmt)
    workouts = result.scalars().all()

    items = []
    for w in workouts:
        exercise_count = len(w.workout_exercises) if w.workout_exercises else 0
        total_sets = 0
        if w.workout_exercises:
            for we in w.workout_exercises:
                if we.sets:
                    total_sets += len(we.sets)

        items.append({
            "id": w.id,
            "user_id": w.user_id,
            "name": w.name,
            "workout_date": w.workout_date,
            "duration_minutes": w.duration_minutes,
            "notes": w.notes,
            "created_at": w.created_at,
            "exercise_count": exercise_count,
            "total_sets": total_sets,
        })

    return items


def get_total_workout_count(db: Session, user_id: int) -> int:
    stmt = select(func.count(Workout.id)).where(Workout.user_id == user_id)
    return db.execute(stmt).scalar() or 0


def get_workouts_this_week(db: Session, user_id: int) -> int:
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    stmt = select(func.count(Workout.id)).where(
        and_(
            Workout.user_id == user_id,
            Workout.workout_date >= start_of_week,
            Workout.workout_date <= end_of_week,
        )
    )
    return db.execute(stmt).scalar() or 0


def get_weekly_activity(db: Session, user_id: int) -> list[dict]:
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())

    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    end_of_week = start_of_week + timedelta(days=6)

    workout_dates = get_workout_dates_for_range(db, user_id, start_of_week, end_of_week)

    activity = []
    for i in range(7):
        current_date = start_of_week + timedelta(days=i)
        activity.append({
            "label": day_labels[i],
            "date_short": current_date.strftime("%d"),
            "has_workout": current_date in workout_dates,
            "is_today": current_date == today,
        })

    return activity


def get_current_streak(db: Session, user_id: int) -> int:
    today = date.today()
    lookback_days = 365

    start_date = today - timedelta(days=lookback_days)
    workout_dates = get_workout_dates_for_range(db, user_id, start_date, today)

    streak = 0
    current_date = today

    while current_date >= start_date:
        if current_date in workout_dates:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            if current_date == today:
                current_date -= timedelta(days=1)
                continue
            break

    return streak


def get_longest_streak(db: Session, user_id: int) -> int:
    stmt = (
        select(Workout.workout_date)
        .where(Workout.user_id == user_id)
        .distinct()
        .order_by(Workout.workout_date.asc())
    )
    result = db.execute(stmt)
    dates_list = sorted([row[0] for row in result.all()])

    if not dates_list:
        return 0

    longest = 1
    current = 1

    for i in range(1, len(dates_list)):
        if dates_list[i] - dates_list[i - 1] == timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    return longest


def get_weekly_average(db: Session, user_id: int) -> float:
    stmt = (
        select(func.min(Workout.workout_date))
        .where(Workout.user_id == user_id)
    )
    first_date = db.execute(stmt).scalar()

    if first_date is None:
        return 0.0

    today = date.today()
    days_diff = (today - first_date).days
    if days_diff <= 0:
        days_diff = 1

    weeks = max(1, days_diff / 7.0)

    total = get_total_workout_count(db, user_id)
    return round(total / weeks, 1)


def get_workouts_this_month(db: Session, user_id: int) -> int:
    today = date.today()
    first_of_month = date(today.year, today.month, 1)

    stmt = select(func.count(Workout.id)).where(
        and_(
            Workout.user_id == user_id,
            Workout.workout_date >= first_of_month,
            Workout.workout_date <= today,
        )
    )
    return db.execute(stmt).scalar() or 0


def get_all_workout_count(db: Session) -> int:
    stmt = select(func.count(Workout.id))
    return db.execute(stmt).scalar() or 0