from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models.workout_template import WorkoutTemplate
from models.template_exercise import TemplateExercise
from models.exercise import Exercise


class TemplateService:

    def __init__(self, db: Session):
        self.db = db

    def create_template(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None,
        is_system: bool = False,
        exercises: Optional[list] = None,
    ) -> WorkoutTemplate:
        template = WorkoutTemplate(
            user_id=user_id,
            name=name.strip(),
            description=description.strip() if description else None,
            is_system=is_system,
            usage_count=0,
        )
        self.db.add(template)
        self.db.flush()

        if exercises:
            for idx, ex_data in enumerate(exercises):
                template_exercise = TemplateExercise(
                    template_id=template.id,
                    exercise_id=int(ex_data["exercise_id"]),
                    sort_order=int(ex_data.get("sort_order", idx + 1)),
                    default_sets=int(ex_data.get("default_sets", 3)),
                    default_reps=int(ex_data.get("default_reps", 10)),
                    default_weight=float(ex_data["default_weight"]) if ex_data.get("default_weight") else None,
                    notes=ex_data.get("notes"),
                )
                self.db.add(template_exercise)

        self.db.commit()
        self.db.refresh(template)
        return template

    def update_template(
        self,
        template_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_system: Optional[bool] = None,
        exercises: Optional[list] = None,
    ) -> Optional[WorkoutTemplate]:
        template = self._get_template_for_owner(template_id, user_id)
        if template is None:
            return None

        if name is not None:
            template.name = name.strip()
        if description is not None:
            template.description = description.strip() if description else None
        if is_system is not None:
            template.is_system = is_system

        if exercises is not None:
            for te in list(template.template_exercises):
                self.db.delete(te)
            self.db.flush()

            for idx, ex_data in enumerate(exercises):
                template_exercise = TemplateExercise(
                    template_id=template.id,
                    exercise_id=int(ex_data["exercise_id"]),
                    sort_order=int(ex_data.get("sort_order", idx + 1)),
                    default_sets=int(ex_data.get("default_sets", 3)),
                    default_reps=int(ex_data.get("default_reps", 10)),
                    default_weight=float(ex_data["default_weight"]) if ex_data.get("default_weight") else None,
                    notes=ex_data.get("notes"),
                )
                self.db.add(template_exercise)

        self.db.commit()
        self.db.refresh(template)
        return template

    def delete_template(self, template_id: int, user_id: int, is_admin: bool = False) -> bool:
        if is_admin:
            template = self.db.execute(
                select(WorkoutTemplate).where(WorkoutTemplate.id == template_id)
            ).scalar_one_or_none()
        else:
            template = self._get_template_for_owner(template_id, user_id)

        if template is None:
            return False

        self.db.delete(template)
        self.db.commit()
        return True

    def clone_template(self, template_id: int, user_id: int) -> Optional[WorkoutTemplate]:
        source = self.get_template_by_id(template_id)
        if source is None:
            return None

        cloned = WorkoutTemplate(
            user_id=user_id,
            name=f"{source.name} (Copy)",
            description=source.description,
            is_system=False,
            usage_count=0,
        )
        self.db.add(cloned)
        self.db.flush()

        for te in source.template_exercises:
            cloned_exercise = TemplateExercise(
                template_id=cloned.id,
                exercise_id=te.exercise_id,
                sort_order=te.sort_order,
                default_sets=te.default_sets,
                default_reps=te.default_reps,
                default_weight=te.default_weight,
                notes=te.notes,
            )
            self.db.add(cloned_exercise)

        self.db.commit()
        self.db.refresh(cloned)
        return cloned

    def list_templates(self, user_id: int) -> dict:
        user_templates_query = (
            select(WorkoutTemplate)
            .options(selectinload(WorkoutTemplate.template_exercises).selectinload(TemplateExercise.exercise))
            .where(
                WorkoutTemplate.user_id == user_id,
                WorkoutTemplate.is_system == False,
            )
            .order_by(WorkoutTemplate.updated_at.desc())
        )
        user_templates = list(self.db.execute(user_templates_query).scalars().all())

        system_templates_query = (
            select(WorkoutTemplate)
            .options(selectinload(WorkoutTemplate.template_exercises).selectinload(TemplateExercise.exercise))
            .where(WorkoutTemplate.is_system == True)
            .order_by(WorkoutTemplate.name.asc())
        )
        system_templates = list(self.db.execute(system_templates_query).scalars().all())

        for tmpl in user_templates + system_templates:
            self._enrich_template_exercises(tmpl)

        return {
            "user_templates": user_templates,
            "system_templates": system_templates,
        }

    def list_all_templates_for_workout(self, user_id: int) -> list:
        query = (
            select(WorkoutTemplate)
            .options(selectinload(WorkoutTemplate.template_exercises).selectinload(TemplateExercise.exercise))
            .where(
                (WorkoutTemplate.user_id == user_id) | (WorkoutTemplate.is_system == True)
            )
            .order_by(WorkoutTemplate.name.asc())
        )
        templates = list(self.db.execute(query).scalars().all())
        for tmpl in templates:
            self._enrich_template_exercises(tmpl)
        return templates

    def list_system_templates(self) -> list:
        query = (
            select(WorkoutTemplate)
            .options(selectinload(WorkoutTemplate.template_exercises).selectinload(TemplateExercise.exercise))
            .where(WorkoutTemplate.is_system == True)
            .order_by(WorkoutTemplate.name.asc())
        )
        templates = list(self.db.execute(query).scalars().all())
        for tmpl in templates:
            self._enrich_template_exercises(tmpl)
        return templates

    def get_template_by_id(self, template_id: int) -> Optional[WorkoutTemplate]:
        query = (
            select(WorkoutTemplate)
            .options(selectinload(WorkoutTemplate.template_exercises).selectinload(TemplateExercise.exercise))
            .where(WorkoutTemplate.id == template_id)
        )
        template = self.db.execute(query).scalar_one_or_none()
        if template:
            self._enrich_template_exercises(template)
        return template

    def get_template_for_api(self, template_id: int) -> Optional[dict]:
        template = self.get_template_by_id(template_id)
        if template is None:
            return None

        exercises_data = []
        for te in sorted(template.template_exercises, key=lambda x: x.sort_order):
            exercise_name = te.exercise.name if te.exercise else f"Exercise #{te.exercise_id}"
            exercises_data.append({
                "exercise_id": te.exercise_id,
                "exercise_name": exercise_name,
                "sort_order": te.sort_order,
                "default_sets": te.default_sets,
                "default_reps": te.default_reps,
                "default_weight": te.default_weight,
                "notes": te.notes,
            })

        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "is_system": template.is_system,
            "usage_count": template.usage_count,
            "exercises": exercises_data,
        }

    def increment_usage_count(self, template_id: int) -> None:
        template = self.db.execute(
            select(WorkoutTemplate).where(WorkoutTemplate.id == template_id)
        ).scalar_one_or_none()
        if template:
            template.usage_count = (template.usage_count or 0) + 1
            self.db.commit()

    def _get_template_for_owner(self, template_id: int, user_id: int) -> Optional[WorkoutTemplate]:
        query = (
            select(WorkoutTemplate)
            .options(selectinload(WorkoutTemplate.template_exercises))
            .where(
                WorkoutTemplate.id == template_id,
                WorkoutTemplate.user_id == user_id,
            )
        )
        return self.db.execute(query).scalar_one_or_none()

    def _enrich_template_exercises(self, template: WorkoutTemplate) -> None:
        for te in template.template_exercises:
            if te.exercise:
                te.exercise_name = te.exercise.name
            else:
                te.exercise_name = f"Exercise #{te.exercise_id}"