import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.orm import Session

from models.workout import Workout
from models.workout_exercise import WorkoutExercise
from models.exercise_set import ExerciseSet
from models.exercise import Exercise
from services.workout_service import (
    get_current_streak,
    get_longest_streak,
    get_weekly_average,
    get_workouts_this_month,
    get_total_workout_count,
)
from services.pr_service import PRService


class ProgressService:

    def __init__(self, db: Session):
        self.db = db

    def get_consistency_stats(self, user_id: int) -> dict:
        current_streak = get_current_streak(self.db, user_id)
        longest_streak = get_longest_streak(self.db, user_id)
        weekly_average = get_weekly_average(self.db, user_id)
        total_this_month = get_workouts_this_month(self.db, user_id)
        total_workouts = get_total_workout_count(self.db, user_id)

        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "weekly_average": weekly_average,
            "total_this_month": total_this_month,
            "total_workouts": total_workouts,
        }

    def get_muscle_group_distribution(self, user_id: int) -> list[dict]:
        stmt = (
            select(
                Exercise.muscle_group,
                func.count(ExerciseSet.id).label("set_count"),
                func.count(func.distinct(Exercise.id)).label("exercise_count"),
            )
            .join(WorkoutExercise, ExerciseSet.workout_exercise_id == WorkoutExercise.id)
            .join(Workout, WorkoutExercise.workout_id == Workout.id)
            .join(Exercise, WorkoutExercise.exercise_id == Exercise.id)
            .where(Workout.user_id == user_id)
            .group_by(Exercise.muscle_group)
            .order_by(func.count(ExerciseSet.id).desc())
        )

        result = self.db.execute(stmt)
        rows = result.all()

        if not rows:
            return []

        total_sets = sum(row.set_count for row in rows)

        distribution = []
        for row in rows:
            percentage = round((row.set_count / total_sets) * 100, 1) if total_sets > 0 else 0.0
            distribution.append({
                "muscle_group": row.muscle_group,
                "count": row.set_count,
                "exercise_count": row.exercise_count,
                "percentage": percentage,
            })

        return distribution

    def get_recent_prs(self, user_id: int, days: int = 30) -> list[dict]:
        pr_service = PRService(self.db)
        return pr_service.get_recent_prs_with_exercise_names(user_id, days=days)

    def get_all_prs(self, user_id: int) -> list[dict]:
        pr_service = PRService(self.db)
        return pr_service.get_all_prs_with_exercise_names(user_id)

    def get_progress_summary(self, user_id: int) -> dict:
        consistency = self.get_consistency_stats(user_id)
        muscle_group_distribution = self.get_muscle_group_distribution(user_id)
        recent_prs = self.get_recent_prs(user_id, days=30)
        all_prs = self.get_all_prs(user_id)

        return {
            "consistency": consistency,
            "muscle_group_distribution": muscle_group_distribution,
            "recent_prs": recent_prs,
            "all_prs": all_prs,
        }