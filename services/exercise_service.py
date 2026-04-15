import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Optional

from sqlalchemy import func, select, delete as sa_delete
from sqlalchemy.orm import Session, selectinload

from models.exercise import Exercise
from models.workout import Workout
from models.workout_exercise import WorkoutExercise
from models.exercise_set import ExerciseSet
from models.personal_record import PersonalRecord


class ExerciseService:

    def __init__(self, db: Session):
        self.db = db

    def list_exercises(
        self,
        search: Optional[str] = None,
        muscle_group: Optional[str] = None,
        equipment: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        query = select(Exercise)

        if search:
            search_term = f"%{search.strip().lower()}%"
            query = query.where(func.lower(Exercise.name).like(search_term))

        if muscle_group:
            query = query.where(func.lower(Exercise.muscle_group) == muscle_group.strip().lower())

        if equipment:
            query = query.where(func.lower(Exercise.equipment) == equipment.strip().lower())

        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        total_pages = max(1, (total + per_page - 1) // per_page)

        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page

        query = query.order_by(Exercise.name).offset(offset).limit(per_page)
        result = self.db.execute(query)
        exercises = result.scalars().all()

        return {
            "exercises": exercises,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    def get_exercise_by_id(self, exercise_id: int) -> Optional[Exercise]:
        result = self.db.execute(
            select(Exercise).where(Exercise.id == exercise_id)
        )
        return result.scalars().first()

    def create_exercise(
        self,
        name: str,
        muscle_group: str,
        equipment: Optional[str] = None,
        instructions: Optional[str] = None,
        is_system: bool = True,
    ) -> Exercise:
        existing = self.db.execute(
            select(Exercise).where(func.lower(Exercise.name) == name.strip().lower())
        ).scalars().first()

        if existing:
            raise ValueError(f"Exercise '{name}' already exists.")

        exercise = Exercise(
            name=name.strip(),
            muscle_group=muscle_group.strip(),
            equipment=equipment.strip() if equipment else None,
            instructions=instructions.strip() if instructions else None,
            is_system=is_system,
        )
        self.db.add(exercise)
        self.db.commit()
        self.db.refresh(exercise)
        return exercise

    def update_exercise(
        self,
        exercise_id: int,
        name: Optional[str] = None,
        muscle_group: Optional[str] = None,
        equipment: Optional[str] = None,
        instructions: Optional[str] = None,
    ) -> Optional[Exercise]:
        exercise = self.get_exercise_by_id(exercise_id)
        if not exercise:
            return None

        if name is not None:
            stripped_name = name.strip()
            if not stripped_name:
                raise ValueError("Exercise name cannot be empty.")
            existing = self.db.execute(
                select(Exercise).where(
                    func.lower(Exercise.name) == stripped_name.lower(),
                    Exercise.id != exercise_id,
                )
            ).scalars().first()
            if existing:
                raise ValueError(f"Exercise '{stripped_name}' already exists.")
            exercise.name = stripped_name

        if muscle_group is not None:
            stripped_mg = muscle_group.strip()
            if not stripped_mg:
                raise ValueError("Muscle group cannot be empty.")
            exercise.muscle_group = stripped_mg

        if equipment is not None:
            exercise.equipment = equipment.strip() if equipment.strip() else None

        if instructions is not None:
            exercise.instructions = instructions.strip() if instructions.strip() else None

        self.db.commit()
        self.db.refresh(exercise)
        return exercise

    def delete_exercise(self, exercise_id: int) -> bool:
        exercise = self.get_exercise_by_id(exercise_id)
        if not exercise:
            return False

        self.db.delete(exercise)
        self.db.commit()
        return True

    def get_exercise_history(
        self,
        user_id: int,
        exercise_id: int,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        base_query = (
            select(
                ExerciseSet.id,
                ExerciseSet.set_number,
                ExerciseSet.weight,
                ExerciseSet.reps,
                ExerciseSet.is_pr,
                ExerciseSet.is_completed,
                Workout.id.label("workout_id"),
                Workout.workout_date,
            )
            .join(WorkoutExercise, ExerciseSet.workout_exercise_id == WorkoutExercise.id)
            .join(Workout, WorkoutExercise.workout_id == Workout.id)
            .where(
                WorkoutExercise.exercise_id == exercise_id,
                Workout.user_id == user_id,
            )
        )

        count_query = select(func.count()).select_from(base_query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        total_pages = max(1, (total + per_page - 1) // per_page)

        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page

        history_query = (
            base_query
            .order_by(Workout.workout_date.desc(), ExerciseSet.set_number.asc())
            .offset(offset)
            .limit(per_page)
        )

        rows = self.db.execute(history_query).all()

        history = []
        for row in rows:
            history.append({
                "id": row.id,
                "set_number": row.set_number,
                "weight": row.weight,
                "reps": row.reps,
                "is_pr": row.is_pr,
                "is_completed": row.is_completed,
                "workout_id": row.workout_id,
                "workout_date": row.workout_date,
            })

        return {
            "history": history,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    def get_personal_records_for_exercise(
        self,
        user_id: int,
        exercise_id: int,
    ) -> list:
        result = self.db.execute(
            select(PersonalRecord).where(
                PersonalRecord.user_id == user_id,
                PersonalRecord.exercise_id == exercise_id,
            )
        )
        return list(result.scalars().all())

    def get_personal_records_map(self, user_id: int) -> dict:
        result = self.db.execute(
            select(PersonalRecord).where(PersonalRecord.user_id == user_id)
        )
        records = result.scalars().all()

        pr_map: dict = {}
        for pr in records:
            if pr.exercise_id not in pr_map:
                pr_map[pr.exercise_id] = {}
            pr_map[pr.exercise_id][pr.record_type] = pr.value

        return pr_map

    def get_muscle_groups(self) -> list[str]:
        result = self.db.execute(
            select(Exercise.muscle_group)
            .distinct()
            .order_by(Exercise.muscle_group)
        )
        return [row[0] for row in result.all() if row[0]]

    def get_equipment_list(self) -> list[str]:
        result = self.db.execute(
            select(Exercise.equipment)
            .where(Exercise.equipment.isnot(None))
            .distinct()
            .order_by(Exercise.equipment)
        )
        return [row[0] for row in result.all() if row[0]]

    def get_all_exercises(self) -> list[Exercise]:
        result = self.db.execute(
            select(Exercise).order_by(Exercise.name)
        )
        return list(result.scalars().all())