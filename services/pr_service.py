from datetime import datetime, date, timedelta, timezone
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from database import get_db
from models.personal_record import PersonalRecord
from models.exercise import Exercise
from models.exercise_set import ExerciseSet
from models.workout_exercise import WorkoutExercise
from models.workout import Workout


class PRService:
    """Service for detecting and managing personal records."""

    def __init__(self, db: Session):
        self.db = db

    def detect_prs(
        self,
        user_id: int,
        exercise_id: int,
        sets: list[dict],
        workout_date: Optional[date] = None,
        set_ids: Optional[list[int]] = None,
    ) -> list[PersonalRecord]:
        """
        Compare workout sets against existing PRs for weight, reps, volume.
        Upserts records idempotently. Returns list of new/updated PRs.

        Each set dict should have: weight (float|None), reps (int), and optionally set_id (int).
        """
        achieved_at = None
        if workout_date:
            achieved_at = datetime.combine(workout_date, datetime.min.time())

        new_prs: list[PersonalRecord] = []

        best_weight: Optional[float] = None
        best_weight_set_id: Optional[int] = None
        best_reps: Optional[int] = None
        best_reps_set_id: Optional[int] = None
        best_volume: Optional[float] = None
        best_volume_set_id: Optional[int] = None

        for i, s in enumerate(sets):
            weight = s.get("weight")
            reps = s.get("reps", 0)
            set_id = s.get("set_id")
            if set_ids and i < len(set_ids):
                set_id = set_ids[i]

            if weight is not None and weight > 0:
                if best_weight is None or weight > best_weight:
                    best_weight = weight
                    best_weight_set_id = set_id

            if reps is not None and reps > 0:
                if best_reps is None or reps > best_reps:
                    best_reps = reps
                    best_reps_set_id = set_id

            if weight is not None and reps is not None and weight > 0 and reps > 0:
                volume = weight * reps
                if best_volume is None or volume > best_volume:
                    best_volume = volume
                    best_volume_set_id = set_id

        candidates = []
        if best_weight is not None:
            candidates.append(("weight", best_weight, best_weight_set_id))
        if best_reps is not None:
            candidates.append(("reps", float(best_reps), best_reps_set_id))
        if best_volume is not None:
            candidates.append(("volume", best_volume, best_volume_set_id))

        for record_type, value, set_id in candidates:
            pr = self._upsert_pr(
                user_id=user_id,
                exercise_id=exercise_id,
                record_type=record_type,
                value=value,
                achieved_at=achieved_at,
                set_id=set_id,
            )
            if pr is not None:
                new_prs.append(pr)

        return new_prs

    def _upsert_pr(
        self,
        user_id: int,
        exercise_id: int,
        record_type: str,
        value: float,
        achieved_at: Optional[datetime] = None,
        set_id: Optional[int] = None,
    ) -> Optional[PersonalRecord]:
        """
        Insert or update a personal record if the new value exceeds the existing one.
        Returns the PR object if created/updated, None if existing PR is higher.
        """
        existing = self.db.execute(
            select(PersonalRecord).where(
                and_(
                    PersonalRecord.user_id == user_id,
                    PersonalRecord.exercise_id == exercise_id,
                    PersonalRecord.record_type == record_type,
                )
            )
        ).scalar_one_or_none()

        if existing is not None:
            if value > existing.value:
                existing.value = value
                existing.achieved_at = achieved_at
                existing.set_id = set_id
                self.db.flush()
                return existing
            return None
        else:
            pr = PersonalRecord(
                user_id=user_id,
                exercise_id=exercise_id,
                record_type=record_type,
                value=value,
                achieved_at=achieved_at,
                set_id=set_id,
            )
            self.db.add(pr)
            self.db.flush()
            return pr

    def get_user_prs(self, user_id: int) -> list[PersonalRecord]:
        """Get all personal records for a user, ordered by exercise and record type."""
        result = self.db.execute(
            select(PersonalRecord)
            .where(PersonalRecord.user_id == user_id)
            .order_by(PersonalRecord.exercise_id, PersonalRecord.record_type)
        )
        return list(result.scalars().all())

    def get_recent_prs(self, user_id: int, days: int = 30) -> list[PersonalRecord]:
        """Get personal records achieved in the last N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_naive = cutoff.replace(tzinfo=None)

        result = self.db.execute(
            select(PersonalRecord)
            .where(
                and_(
                    PersonalRecord.user_id == user_id,
                    PersonalRecord.achieved_at.isnot(None),
                    PersonalRecord.achieved_at >= cutoff_naive,
                )
            )
            .order_by(PersonalRecord.achieved_at.desc())
        )
        return list(result.scalars().all())

    def get_exercise_prs(self, user_id: int, exercise_id: int) -> list[PersonalRecord]:
        """Get all personal records for a specific exercise and user."""
        result = self.db.execute(
            select(PersonalRecord)
            .where(
                and_(
                    PersonalRecord.user_id == user_id,
                    PersonalRecord.exercise_id == exercise_id,
                )
            )
            .order_by(PersonalRecord.record_type)
        )
        return list(result.scalars().all())

    def get_exercise_prs_map(self, user_id: int) -> dict[int, dict[str, float]]:
        """
        Get a mapping of exercise_id -> {record_type: value} for all user PRs.
        Useful for displaying PR badges on exercise library cards.
        """
        prs = self.get_user_prs(user_id)
        pr_map: dict[int, dict[str, float]] = {}
        for pr in prs:
            if pr.exercise_id not in pr_map:
                pr_map[pr.exercise_id] = {}
            pr_map[pr.exercise_id][pr.record_type] = pr.value
        return pr_map

    def get_all_prs_with_exercise_names(self, user_id: int) -> list[dict]:
        """
        Get all PRs for a user with exercise names included.
        Returns a list of dicts with exercise_name, exercise_id, best_weight,
        best_reps, best_volume, and date_achieved.
        """
        prs = self.get_user_prs(user_id)

        exercise_ids = list({pr.exercise_id for pr in prs})
        exercise_map: dict[int, str] = {}
        if exercise_ids:
            exercises = self.db.execute(
                select(Exercise).where(Exercise.id.in_(exercise_ids))
            ).scalars().all()
            exercise_map = {e.id: e.name for e in exercises}

        grouped: dict[int, dict] = {}
        for pr in prs:
            if pr.exercise_id not in grouped:
                grouped[pr.exercise_id] = {
                    "exercise_id": pr.exercise_id,
                    "exercise_name": exercise_map.get(pr.exercise_id, "Unknown Exercise"),
                    "best_weight": None,
                    "best_reps": None,
                    "best_volume": None,
                    "date_achieved": None,
                }
            entry = grouped[pr.exercise_id]
            if pr.record_type == "weight":
                entry["best_weight"] = pr.value
            elif pr.record_type == "reps":
                entry["best_reps"] = pr.value
            elif pr.record_type == "volume":
                entry["best_volume"] = pr.value

            if pr.achieved_at is not None:
                if entry["date_achieved"] is None or pr.achieved_at > entry["date_achieved"]:
                    entry["date_achieved"] = pr.achieved_at

        return list(grouped.values())

    def get_recent_prs_with_exercise_names(self, user_id: int, days: int = 30) -> list[dict]:
        """
        Get recent PRs with exercise names for display on progress page.
        Returns list of dicts with exercise_name, record_type, value, achieved_date.
        """
        prs = self.get_recent_prs(user_id, days=days)

        exercise_ids = list({pr.exercise_id for pr in prs})
        exercise_map: dict[int, str] = {}
        if exercise_ids:
            exercises = self.db.execute(
                select(Exercise).where(Exercise.id.in_(exercise_ids))
            ).scalars().all()
            exercise_map = {e.id: e.name for e in exercises}

        results = []
        for pr in prs:
            results.append({
                "exercise_name": exercise_map.get(pr.exercise_id, "Unknown Exercise"),
                "exercise_id": pr.exercise_id,
                "record_type": pr.record_type,
                "value": pr.value,
                "achieved_date": pr.achieved_at,
            })
        return results

    def detect_prs_for_workout(self, user_id: int, workout_id: int) -> list[PersonalRecord]:
        """
        Detect PRs for all exercises in a given workout.
        Marks sets with is_pr flag and upserts personal_records table.
        """
        workout = self.db.execute(
            select(Workout).where(
                and_(
                    Workout.id == workout_id,
                    Workout.user_id == user_id,
                )
            )
        ).scalar_one_or_none()

        if workout is None:
            return []

        workout_exercises = self.db.execute(
            select(WorkoutExercise).where(WorkoutExercise.workout_id == workout_id)
        ).scalars().all()

        all_new_prs: list[PersonalRecord] = []

        for we in workout_exercises:
            exercise_sets = self.db.execute(
                select(ExerciseSet).where(ExerciseSet.workout_exercise_id == we.id)
                .order_by(ExerciseSet.set_number)
            ).scalars().all()

            sets_data = []
            set_ids = []
            for s in exercise_sets:
                sets_data.append({
                    "weight": s.weight,
                    "reps": s.reps,
                    "set_id": s.id,
                })
                set_ids.append(s.id)

            new_prs = self.detect_prs(
                user_id=user_id,
                exercise_id=we.exercise_id,
                sets=sets_data,
                workout_date=workout.workout_date,
                set_ids=set_ids,
            )

            pr_set_ids = {pr.set_id for pr in new_prs if pr.set_id is not None}
            for s in exercise_sets:
                s.is_pr = s.id in pr_set_ids

            all_new_prs.extend(new_prs)

        self.db.flush()
        return all_new_prs