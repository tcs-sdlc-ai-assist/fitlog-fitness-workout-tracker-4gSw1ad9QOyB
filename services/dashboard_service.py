import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func, select, and_, distinct
from sqlalchemy.orm import Session

from models.user import User
from models.workout import Workout
from models.exercise import Exercise
from models.workout_template import WorkoutTemplate
from services.workout_service import (
    get_recent_workouts,
    get_total_workout_count,
    get_workouts_this_week,
    get_weekly_activity,
    get_current_streak,
    get_longest_streak,
    get_weekly_average,
    get_workouts_this_month,
    get_all_workout_count,
)
from services.measurement_service import MeasurementService
from services.pr_service import PRService


class DashboardService:

    def __init__(self, db: Session):
        self.db = db

    def get_user_dashboard_data(self, user_id: int) -> dict:
        """Get all data needed for the user dashboard page."""

        workouts_this_week = get_workouts_this_week(self.db, user_id)
        current_streak = get_current_streak(self.db, user_id)
        total_workouts = get_total_workout_count(self.db, user_id)

        measurement_service = MeasurementService(self.db)
        latest_weight = measurement_service.get_latest_weight(user_id)

        weekly_activity = get_weekly_activity(self.db, user_id)

        recent_workouts = get_recent_workouts(self.db, user_id, limit=5)

        pr_service = PRService(self.db)
        recent_prs_raw = pr_service.get_recent_prs_with_exercise_names(user_id, days=30)

        personal_records = []
        for pr in recent_prs_raw[:3]:
            personal_records.append({
                "exercise_name": pr.get("exercise_name", "Unknown Exercise"),
                "exercise_id": pr.get("exercise_id"),
                "record_type": pr.get("record_type", ""),
                "value": pr.get("value", 0),
                "achieved_at": _format_date(pr.get("achieved_date")),
            })

        user = self.db.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()

        display_name = user.display_name if user else "User"

        return {
            "display_name": display_name,
            "workouts_this_week": workouts_this_week,
            "current_streak": current_streak,
            "total_workouts": total_workouts,
            "latest_weight": latest_weight,
            "weekly_activity": weekly_activity,
            "recent_workouts": recent_workouts,
            "personal_records": personal_records,
        }

    def get_admin_dashboard_data(self) -> dict:
        """Get all data needed for the admin dashboard page."""

        total_users = self.db.execute(
            select(func.count(User.id))
        ).scalar() or 0

        total_workouts = get_all_workout_count(self.db)

        total_exercises = self.db.execute(
            select(func.count(Exercise.id))
        ).scalar() or 0

        active_users_7d = self._get_active_users_count(days=7)

        users = self.db.execute(
            select(User).order_by(User.created_at.desc())
        ).scalars().all()

        exercises = self.db.execute(
            select(Exercise).order_by(Exercise.name.asc())
        ).scalars().all()

        system_templates = self.db.execute(
            select(WorkoutTemplate).where(WorkoutTemplate.is_system == True).order_by(WorkoutTemplate.name.asc())
        ).scalars().all()

        stats = {
            "total_users": total_users,
            "total_workouts": total_workouts,
            "total_exercises": total_exercises,
            "active_users_7d": active_users_7d,
        }

        return {
            "stats": stats,
            "users": list(users),
            "exercises": list(exercises),
            "system_templates": list(system_templates),
        }

    def _get_active_users_count(self, days: int = 7) -> int:
        """Count distinct users who have logged a workout in the last N days."""
        cutoff_date = date.today() - timedelta(days=days)

        result = self.db.execute(
            select(func.count(distinct(Workout.user_id))).where(
                Workout.workout_date >= cutoff_date
            )
        )
        return result.scalar() or 0


def _format_date(dt) -> Optional[str]:
    """Format a datetime or date object to a display string, or return None."""
    if dt is None:
        return None
    try:
        if hasattr(dt, "strftime"):
            return dt.strftime("%b %d, %Y")
        return str(dt)
    except Exception:
        return str(dt)