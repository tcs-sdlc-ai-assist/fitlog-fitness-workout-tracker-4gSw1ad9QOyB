import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from tests.conftest import *
from models.exercise import Exercise
from models.workout_template import WorkoutTemplate
from models.template_exercise import TemplateExercise
from utils.security import create_access_token


def _create_exercises(db, count=3):
    """Helper to create test exercises."""
    exercises = []
    for i in range(count):
        exercise = Exercise(
            name=f"Test Exercise {i + 1}",
            muscle_group="chest",
            equipment="barbell",
            instructions=f"Instructions for exercise {i + 1}",
            is_system=True,
        )
        db.add(exercise)
    db.commit()
    exercises = db.query(Exercise).order_by(Exercise.id).all()
    return exercises


def _create_user_template(db, user_id, name="My Template", exercises=None):
    """Helper to create a user-owned template."""
    template = WorkoutTemplate(
        user_id=user_id,
        name=name,
        description="A test template",
        is_system=False,
        usage_count=0,
    )
    db.add(template)
    db.flush()

    if exercises:
        for idx, ex in enumerate(exercises):
            te = TemplateExercise(
                template_id=template.id,
                exercise_id=ex.id,
                sort_order=idx + 1,
                default_sets=3,
                default_reps=10,
                default_weight=None,
                notes=None,
            )
            db.add(te)

    db.commit()
    db.refresh(template)
    return template


def _create_system_template(db, name="System Template", exercises=None):
    """Helper to create a system template."""
    template = WorkoutTemplate(
        user_id=None,
        name=name,
        description="A system template",
        is_system=True,
        usage_count=0,
    )
    db.add(template)
    db.flush()

    if exercises:
        for idx, ex in enumerate(exercises):
            te = TemplateExercise(
                template_id=template.id,
                exercise_id=ex.id,
                sort_order=idx + 1,
                default_sets=4,
                default_reps=8,
                default_weight=60.0,
                notes=None,
            )
            db.add(te)

    db.commit()
    db.refresh(template)
    return template


class TestListTemplates:
    """Tests for GET /templates."""

    def test_list_templates_requires_auth(self, test_client):
        response = test_client.get("/templates", follow_redirects=False)
        assert response.status_code == 401 or response.status_code == 302

    def test_list_templates_shows_user_templates(self, authenticated_client, test_db, test_user):
        exercises = _create_exercises(test_db, 2)
        _create_user_template(test_db, test_user.id, "My Push Day", exercises)
        _create_user_template(test_db, test_user.id, "My Pull Day", exercises)

        response = authenticated_client.get("/templates")
        assert response.status_code == 200
        assert "My Push Day" in response.text
        assert "My Pull Day" in response.text

    def test_list_templates_shows_system_templates(self, authenticated_client, test_db):
        exercises = _create_exercises(test_db, 2)
        _create_system_template(test_db, "Full Body System", exercises)

        response = authenticated_client.get("/templates")
        assert response.status_code == 200
        assert "Full Body System" in response.text
        assert "System" in response.text

    def test_list_templates_shows_both_user_and_system(self, authenticated_client, test_db, test_user):
        exercises = _create_exercises(test_db, 2)
        _create_user_template(test_db, test_user.id, "User Custom Template", exercises)
        _create_system_template(test_db, "System PPL Template", exercises)

        response = authenticated_client.get("/templates")
        assert response.status_code == 200
        assert "User Custom Template" in response.text
        assert "System PPL Template" in response.text

    def test_list_templates_does_not_show_other_users_templates(self, authenticated_client, test_db, admin_user):
        exercises = _create_exercises(test_db, 1)
        _create_user_template(test_db, admin_user.id, "Admin Private Template", exercises)

        response = authenticated_client.get("/templates")
        assert response.status_code == 200
        assert "Admin Private Template" not in response.text

    def test_list_templates_empty_state(self, authenticated_client):
        response = authenticated_client.get("/templates")
        assert response.status_code == 200
        assert "No templates yet" in response.text or "Create Template" in response.text


class TestCreateTemplate:
    """Tests for GET /templates/new and POST /templates/new."""

    def test_new_template_form_renders(self, authenticated_client, test_db):
        _create_exercises(test_db, 2)
        response = authenticated_client.get("/templates/new")
        assert response.status_code == 200
        assert "Create New Template" in response.text or "New Template" in response.text

    def test_create_template_success(self, authenticated_client, test_db, test_user):
        exercises = _create_exercises(test_db, 2)

        form_data = {
            "name": "My New Template",
            "description": "A brand new template",
            "exercises[0][exercise_id]": str(exercises[0].id),
            "exercises[0][sort_order]": "1",
            "exercises[0][default_sets]": "3",
            "exercises[0][default_reps]": "10",
            "exercises[0][default_weight]": "",
        }

        response = authenticated_client.post("/templates/new", data=form_data, follow_redirects=False)
        assert response.status_code in (302, 303)

        template = test_db.query(WorkoutTemplate).filter(
            WorkoutTemplate.name == "My New Template",
            WorkoutTemplate.user_id == test_user.id,
        ).first()
        assert template is not None
        assert template.description == "A brand new template"
        assert template.is_system is False

    def test_create_template_with_multiple_exercises(self, authenticated_client, test_db, test_user):
        exercises = _create_exercises(test_db, 3)

        form_data = {
            "name": "Multi Exercise Template",
            "description": "",
            "exercises[0][exercise_id]": str(exercises[0].id),
            "exercises[0][sort_order]": "1",
            "exercises[0][default_sets]": "4",
            "exercises[0][default_reps]": "8",
            "exercises[0][default_weight]": "60",
            "exercises[1][exercise_id]": str(exercises[1].id),
            "exercises[1][sort_order]": "2",
            "exercises[1][default_sets]": "3",
            "exercises[1][default_reps]": "12",
            "exercises[1][default_weight]": "",
            "exercises[2][exercise_id]": str(exercises[2].id),
            "exercises[2][sort_order]": "3",
            "exercises[2][default_sets]": "3",
            "exercises[2][default_reps]": "15",
            "exercises[2][default_weight]": "20.5",
        }

        response = authenticated_client.post("/templates/new", data=form_data, follow_redirects=False)
        assert response.status_code in (302, 303)

        template = test_db.query(WorkoutTemplate).filter(
            WorkoutTemplate.name == "Multi Exercise Template",
            WorkoutTemplate.user_id == test_user.id,
        ).first()
        assert template is not None

        template_exercises = test_db.query(TemplateExercise).filter(
            TemplateExercise.template_id == template.id,
        ).order_by(TemplateExercise.sort_order).all()
        assert len(template_exercises) == 3
        assert template_exercises[0].exercise_id == exercises[0].id
        assert template_exercises[0].default_sets == 4
        assert template_exercises[0].default_reps == 8
        assert template_exercises[0].default_weight == 60.0
        assert template_exercises[2].default_weight == 20.5

    def test_create_template_requires_auth(self, test_client):
        response = test_client.post("/templates/new", data={"name": "Test"}, follow_redirects=False)
        assert response.status_code in (401, 302)


class TestTemplateDetail:
    """Tests for GET /templates/{template_id}."""

    def test_view_own_template(self, authenticated_client, test_db, test_user):
        exercises = _create_exercises(test_db, 2)
        template = _create_user_template(test_db, test_user.id, "My Detail Template", exercises)

        response = authenticated_client.get(f"/templates/{template.id}")
        assert response.status_code == 200
        assert "My Detail Template" in response.text
        assert "A test template" in response.text

    def test_view_system_template(self, authenticated_client, test_db):
        exercises = _create_exercises(test_db, 2)
        template = _create_system_template(test_db, "System Detail Template", exercises)

        response = authenticated_client.get(f"/templates/{template.id}")
        assert response.status_code == 200
        assert "System Detail Template" in response.text

    def test_view_other_users_template_forbidden(self, authenticated_client, test_db, admin_user):
        exercises = _create_exercises(test_db, 1)
        template = _create_user_template(test_db, admin_user.id, "Admin Only Template", exercises)

        response = authenticated_client.get(f"/templates/{template.id}", follow_redirects=False)
        assert response.status_code in (302, 303)

    def test_view_nonexistent_template(self, authenticated_client):
        response = authenticated_client.get("/templates/99999", follow_redirects=False)
        assert response.status_code in (302, 303)


class TestEditTemplate:
    """Tests for GET /templates/{id}/edit and POST /templates/{id}/edit."""

    def test_edit_form_renders_for_owner(self, authenticated_client, test_db, test_user):
        exercises = _create_exercises(test_db, 2)
        template = _create_user_template(test_db, test_user.id, "Editable Template", exercises)

        response = authenticated_client.get(f"/templates/{template.id}/edit")
        assert response.status_code == 200
        assert "Editable Template" in response.text

    def test_edit_template_success(self, authenticated_client, test_db, test_user):
        exercises = _create_exercises(test_db, 2)
        template = _create_user_template(test_db, test_user.id, "Old Name", exercises)

        form_data = {
            "name": "Updated Name",
            "description": "Updated description",
            "exercises[0][exercise_id]": str(exercises[0].id),
            "exercises[0][sort_order]": "1",
            "exercises[0][default_sets]": "5",
            "exercises[0][default_reps]": "5",
            "exercises[0][default_weight]": "100",
        }

        response = authenticated_client.post(
            f"/templates/{template.id}/edit",
            data=form_data,
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)

        test_db.refresh(template)
        assert template.name == "Updated Name"
        assert template.description == "Updated description"

    def test_edit_template_forbidden_for_non_owner(self, authenticated_client, test_db, admin_user):
        exercises = _create_exercises(test_db, 1)
        template = _create_user_template(test_db, admin_user.id, "Not My Template", exercises)

        response = authenticated_client.get(f"/templates/{template.id}/edit", follow_redirects=False)
        assert response.status_code in (302, 303)

    def test_edit_nonexistent_template(self, authenticated_client):
        response = authenticated_client.get("/templates/99999/edit", follow_redirects=False)
        assert response.status_code in (302, 303)

    def test_edit_template_post_forbidden_for_non_owner(self, authenticated_client, test_db, admin_user):
        exercises = _create_exercises(test_db, 1)
        template = _create_user_template(test_db, admin_user.id, "Not Mine", exercises)

        form_data = {
            "name": "Hacked Name",
            "description": "",
            "exercises[0][exercise_id]": str(exercises[0].id),
            "exercises[0][sort_order]": "1",
            "exercises[0][default_sets]": "3",
            "exercises[0][default_reps]": "10",
            "exercises[0][default_weight]": "",
        }

        response = authenticated_client.post(
            f"/templates/{template.id}/edit",
            data=form_data,
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)

        test_db.refresh(template)
        assert template.name == "Not Mine"


class TestDeleteTemplate:
    """Tests for POST /templates/{id}/delete."""

    def test_delete_own_template(self, authenticated_client, test_db, test_user):
        exercises = _create_exercises(test_db, 1)
        template = _create_user_template(test_db, test_user.id, "To Delete", exercises)
        template_id = template.id

        response = authenticated_client.post(
            f"/templates/{template_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)

        deleted = test_db.query(WorkoutTemplate).filter(WorkoutTemplate.id == template_id).first()
        assert deleted is None

    def test_delete_template_cascades_exercises(self, authenticated_client, test_db, test_user):
        exercises = _create_exercises(test_db, 2)
        template = _create_user_template(test_db, test_user.id, "Cascade Delete", exercises)
        template_id = template.id

        te_count_before = test_db.query(TemplateExercise).filter(
            TemplateExercise.template_id == template_id
        ).count()
        assert te_count_before == 2

        response = authenticated_client.post(
            f"/templates/{template_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)

        te_count_after = test_db.query(TemplateExercise).filter(
            TemplateExercise.template_id == template_id
        ).count()
        assert te_count_after == 0

    def test_delete_template_forbidden_for_non_owner(self, authenticated_client, test_db, admin_user):
        exercises = _create_exercises(test_db, 1)
        template = _create_user_template(test_db, admin_user.id, "Admin Template", exercises)
        template_id = template.id

        response = authenticated_client.post(
            f"/templates/{template_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)

        still_exists = test_db.query(WorkoutTemplate).filter(WorkoutTemplate.id == template_id).first()
        assert still_exists is not None

    def test_delete_nonexistent_template(self, authenticated_client):
        response = authenticated_client.post("/templates/99999/delete", follow_redirects=False)
        assert response.status_code in (302, 303)


class TestCloneTemplate:
    """Tests for POST /templates/{id}/clone."""

    def test_clone_system_template(self, authenticated_client, test_db, test_user):
        exercises = _create_exercises(test_db, 3)
        system_template = _create_system_template(test_db, "Push Pull Legs", exercises)

        response = authenticated_client.post(
            f"/templates/{system_template.id}/clone",
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)

        cloned = test_db.query(WorkoutTemplate).filter(
            WorkoutTemplate.user_id == test_user.id,
            WorkoutTemplate.name.like("%Push Pull Legs%Copy%"),
        ).first()
        assert cloned is not None
        assert cloned.is_system is False
        assert cloned.user_id == test_user.id

        cloned_exercises = test_db.query(TemplateExercise).filter(
            TemplateExercise.template_id == cloned.id,
        ).order_by(TemplateExercise.sort_order).all()
        assert len(cloned_exercises) == 3

    def test_clone_preserves_exercise_details(self, authenticated_client, test_db, test_user):
        exercises = _create_exercises(test_db, 2)
        system_template = _create_system_template(test_db, "Detail Clone", exercises)

        response = authenticated_client.post(
            f"/templates/{system_template.id}/clone",
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)

        cloned = test_db.query(WorkoutTemplate).filter(
            WorkoutTemplate.user_id == test_user.id,
            WorkoutTemplate.name.like("%Detail Clone%"),
        ).first()
        assert cloned is not None

        original_exercises = test_db.query(TemplateExercise).filter(
            TemplateExercise.template_id == system_template.id,
        ).order_by(TemplateExercise.sort_order).all()

        cloned_exercises = test_db.query(TemplateExercise).filter(
            TemplateExercise.template_id == cloned.id,
        ).order_by(TemplateExercise.sort_order).all()

        assert len(cloned_exercises) == len(original_exercises)
        for orig, clone in zip(original_exercises, cloned_exercises):
            assert clone.exercise_id == orig.exercise_id
            assert clone.default_sets == orig.default_sets
            assert clone.default_reps == orig.default_reps
            assert clone.default_weight == orig.default_weight
            assert clone.sort_order == orig.sort_order

    def test_clone_user_template(self, authenticated_client, test_db, test_user):
        exercises = _create_exercises(test_db, 1)
        own_template = _create_user_template(test_db, test_user.id, "My Original", exercises)

        response = authenticated_client.post(
            f"/templates/{own_template.id}/clone",
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)

        clones = test_db.query(WorkoutTemplate).filter(
            WorkoutTemplate.user_id == test_user.id,
            WorkoutTemplate.name.like("%My Original%Copy%"),
        ).all()
        assert len(clones) == 1

    def test_clone_nonexistent_template(self, authenticated_client):
        response = authenticated_client.post("/templates/99999/clone", follow_redirects=False)
        assert response.status_code in (302, 303)

    def test_clone_does_not_modify_original(self, authenticated_client, test_db, test_user):
        exercises = _create_exercises(test_db, 2)
        system_template = _create_system_template(test_db, "Immutable Original", exercises)
        original_name = system_template.name
        original_exercise_count = test_db.query(TemplateExercise).filter(
            TemplateExercise.template_id == system_template.id,
        ).count()

        authenticated_client.post(
            f"/templates/{system_template.id}/clone",
            follow_redirects=False,
        )

        test_db.refresh(system_template)
        assert system_template.name == original_name
        assert system_template.is_system is True

        current_exercise_count = test_db.query(TemplateExercise).filter(
            TemplateExercise.template_id == system_template.id,
        ).count()
        assert current_exercise_count == original_exercise_count


class TestTemplateAPIEndpoint:
    """Tests for GET /api/templates/{template_id}."""

    def test_api_get_system_template(self, authenticated_client, test_db):
        exercises = _create_exercises(test_db, 2)
        template = _create_system_template(test_db, "API System Template", exercises)

        response = authenticated_client.get(f"/api/templates/{template.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "API System Template"
        assert data["is_system"] is True
        assert len(data["exercises"]) == 2

    def test_api_get_own_template(self, authenticated_client, test_db, test_user):
        exercises = _create_exercises(test_db, 1)
        template = _create_user_template(test_db, test_user.id, "API User Template", exercises)

        response = authenticated_client.get(f"/api/templates/{template.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "API User Template"
        assert data["is_system"] is False

    def test_api_get_other_users_template_forbidden(self, authenticated_client, test_db, admin_user):
        exercises = _create_exercises(test_db, 1)
        template = _create_user_template(test_db, admin_user.id, "Admin API Template", exercises)

        response = authenticated_client.get(f"/api/templates/{template.id}")
        assert response.status_code == 403

    def test_api_get_nonexistent_template(self, authenticated_client):
        response = authenticated_client.get("/api/templates/99999")
        assert response.status_code == 404


class TestAdminTemplateManagement:
    """Tests for admin template operations."""

    def test_admin_can_edit_system_template(self, admin_client, test_db, admin_user):
        exercises = _create_exercises(test_db, 2)
        template = _create_system_template(test_db, "Admin Editable", exercises)

        response = admin_client.get(f"/admin/templates/{template.id}/edit")
        assert response.status_code == 200

    def test_admin_can_delete_system_template(self, admin_client, test_db, admin_user):
        exercises = _create_exercises(test_db, 1)
        template = _create_system_template(test_db, "Admin Deletable", exercises)
        template_id = template.id

        response = admin_client.post(
            f"/admin/templates/{template_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)

        deleted = test_db.query(WorkoutTemplate).filter(WorkoutTemplate.id == template_id).first()
        assert deleted is None

    def test_admin_can_create_system_template(self, admin_client, test_db):
        form_data = {
            "name": "New System Template",
            "description": "Created by admin",
            "is_system": "true",
        }

        response = admin_client.post("/admin/templates", data=form_data, follow_redirects=False)
        assert response.status_code in (302, 303)

        template = test_db.query(WorkoutTemplate).filter(
            WorkoutTemplate.name == "New System Template",
        ).first()
        assert template is not None
        assert template.is_system is True

    def test_regular_user_cannot_access_admin_template_routes(self, authenticated_client, test_db):
        exercises = _create_exercises(test_db, 1)
        template = _create_system_template(test_db, "Protected Template", exercises)

        response = authenticated_client.get(
            f"/admin/templates/{template.id}/edit",
            follow_redirects=False,
        )
        assert response.status_code in (302, 303, 401, 403)

        response = authenticated_client.post(
            f"/admin/templates/{template.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code in (302, 303, 401, 403)

        still_exists = test_db.query(WorkoutTemplate).filter(
            WorkoutTemplate.id == template.id
        ).first()
        assert still_exists is not None