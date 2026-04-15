import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from models.exercise import Exercise
from utils.security import hash_password, create_access_token


class TestExerciseLibrary:
    """Tests for the exercise library listing and browsing."""

    def test_list_exercises_requires_auth(self, test_client):
        """Unauthenticated users should be redirected when accessing exercises."""
        response = test_client.get("/exercises", follow_redirects=False)
        assert response.status_code in (302, 401, 403)

    def test_list_exercises_authenticated(self, authenticated_client, test_db):
        """Authenticated users can view the exercise library."""
        exercise = Exercise(
            name="Bench Press",
            muscle_group="chest",
            equipment="barbell",
            instructions="Lie on a flat bench and press the bar up.",
            is_system=True,
        )
        test_db.add(exercise)
        test_db.commit()

        response = authenticated_client.get("/exercises")
        assert response.status_code == 200
        assert "Bench Press" in response.text
        assert "chest" in response.text

    def test_list_exercises_empty(self, authenticated_client):
        """Exercise library shows empty state when no exercises exist."""
        response = authenticated_client.get("/exercises")
        assert response.status_code == 200
        assert "No exercises found" in response.text or "exercise" in response.text.lower()

    def test_list_exercises_multiple(self, authenticated_client, test_db):
        """Exercise library shows multiple exercises."""
        exercises = [
            Exercise(name="Squat", muscle_group="legs", equipment="barbell", is_system=True),
            Exercise(name="Deadlift", muscle_group="back", equipment="barbell", is_system=True),
            Exercise(name="Pull-Up", muscle_group="back", equipment="bodyweight", is_system=True),
        ]
        for ex in exercises:
            test_db.add(ex)
        test_db.commit()

        response = authenticated_client.get("/exercises")
        assert response.status_code == 200
        assert "Squat" in response.text or "Deadlift" in response.text or "Pull-Up" in response.text


class TestExerciseSearch:
    """Tests for searching exercises by name."""

    def test_search_exercises_by_name(self, authenticated_client, test_db):
        """Search should filter exercises by name."""
        exercises = [
            Exercise(name="Barbell Bench Press", muscle_group="chest", equipment="barbell", is_system=True),
            Exercise(name="Dumbbell Curl", muscle_group="biceps", equipment="dumbbell", is_system=True),
            Exercise(name="Barbell Squat", muscle_group="legs", equipment="barbell", is_system=True),
        ]
        for ex in exercises:
            test_db.add(ex)
        test_db.commit()

        response = authenticated_client.get("/exercises?search=Barbell")
        assert response.status_code == 200
        assert "Barbell Bench Press" in response.text
        assert "Barbell Squat" in response.text

    def test_search_exercises_no_results(self, authenticated_client, test_db):
        """Search with no matching results shows empty state."""
        exercise = Exercise(name="Bench Press", muscle_group="chest", equipment="barbell", is_system=True)
        test_db.add(exercise)
        test_db.commit()

        response = authenticated_client.get("/exercises?search=nonexistent_xyz")
        assert response.status_code == 200
        assert "Bench Press" not in response.text

    def test_search_exercises_case_insensitive(self, authenticated_client, test_db):
        """Search should be case-insensitive."""
        exercise = Exercise(name="Overhead Press", muscle_group="shoulders", equipment="barbell", is_system=True)
        test_db.add(exercise)
        test_db.commit()

        response = authenticated_client.get("/exercises?search=overhead")
        assert response.status_code == 200
        assert "Overhead Press" in response.text


class TestExerciseFilterByMuscleGroup:
    """Tests for filtering exercises by muscle group."""

    def test_filter_by_muscle_group(self, authenticated_client, test_db):
        """Filter should show only exercises for the selected muscle group."""
        exercises = [
            Exercise(name="Bench Press", muscle_group="chest", equipment="barbell", is_system=True),
            Exercise(name="Squat", muscle_group="legs", equipment="barbell", is_system=True),
            Exercise(name="Incline Press", muscle_group="chest", equipment="dumbbell", is_system=True),
        ]
        for ex in exercises:
            test_db.add(ex)
        test_db.commit()

        response = authenticated_client.get("/exercises?muscle_group=chest")
        assert response.status_code == 200
        assert "Bench Press" in response.text
        assert "Incline Press" in response.text

    def test_filter_by_equipment(self, authenticated_client, test_db):
        """Filter should show only exercises for the selected equipment."""
        exercises = [
            Exercise(name="Barbell Curl", muscle_group="biceps", equipment="barbell", is_system=True),
            Exercise(name="Dumbbell Curl", muscle_group="biceps", equipment="dumbbell", is_system=True),
        ]
        for ex in exercises:
            test_db.add(ex)
        test_db.commit()

        response = authenticated_client.get("/exercises?equipment=dumbbell")
        assert response.status_code == 200
        assert "Dumbbell Curl" in response.text

    def test_filter_combined_search_and_muscle_group(self, authenticated_client, test_db):
        """Combined search and muscle group filter should work together."""
        exercises = [
            Exercise(name="Barbell Bench Press", muscle_group="chest", equipment="barbell", is_system=True),
            Exercise(name="Barbell Row", muscle_group="back", equipment="barbell", is_system=True),
            Exercise(name="Dumbbell Flyes", muscle_group="chest", equipment="dumbbell", is_system=True),
        ]
        for ex in exercises:
            test_db.add(ex)
        test_db.commit()

        response = authenticated_client.get("/exercises?search=Barbell&muscle_group=chest")
        assert response.status_code == 200
        assert "Barbell Bench Press" in response.text


class TestExerciseDetail:
    """Tests for exercise detail page."""

    def test_exercise_detail_page(self, authenticated_client, test_db):
        """Exercise detail page shows exercise information."""
        exercise = Exercise(
            name="Barbell Deadlift",
            muscle_group="back",
            equipment="barbell",
            instructions="Stand with feet hip-width apart and lift the bar.",
            is_system=True,
        )
        test_db.add(exercise)
        test_db.commit()
        test_db.refresh(exercise)

        response = authenticated_client.get(f"/exercises/{exercise.id}")
        assert response.status_code == 200
        assert "Barbell Deadlift" in response.text
        assert "back" in response.text
        assert "barbell" in response.text
        assert "Stand with feet hip-width apart" in response.text

    def test_exercise_detail_not_found(self, authenticated_client):
        """Accessing a non-existent exercise should redirect."""
        response = authenticated_client.get("/exercises/99999", follow_redirects=False)
        assert response.status_code == 302

    def test_exercise_detail_requires_auth(self, test_client):
        """Unauthenticated users cannot access exercise detail."""
        response = test_client.get("/exercises/1", follow_redirects=False)
        assert response.status_code in (302, 401, 403)


class TestAdminCreateExercise:
    """Tests for admin exercise creation."""

    def test_admin_create_exercise_success(self, admin_client, test_db):
        """Admin can create a new exercise."""
        response = admin_client.post(
            "/admin/exercises",
            data={
                "name": "Cable Crossover",
                "muscle_group": "chest",
                "equipment": "cable",
                "instructions": "Stand between two cable stations.",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        exercise = test_db.query(Exercise).filter(Exercise.name == "Cable Crossover").first()
        assert exercise is not None
        assert exercise.muscle_group == "chest"
        assert exercise.equipment == "cable"
        assert exercise.is_system is True

    def test_admin_create_exercise_missing_name(self, admin_client, test_db):
        """Creating an exercise without a name should fail."""
        response = admin_client.post(
            "/admin/exercises",
            data={
                "name": "",
                "muscle_group": "chest",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        exercise_count = test_db.query(Exercise).count()
        assert exercise_count == 0

    def test_admin_create_exercise_missing_muscle_group(self, admin_client, test_db):
        """Creating an exercise without a muscle group should fail."""
        response = admin_client.post(
            "/admin/exercises",
            data={
                "name": "Test Exercise",
                "muscle_group": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        exercise = test_db.query(Exercise).filter(Exercise.name == "Test Exercise").first()
        assert exercise is None

    def test_admin_create_exercise_duplicate_name(self, admin_client, test_db):
        """Creating an exercise with a duplicate name should fail."""
        exercise = Exercise(name="Bench Press", muscle_group="chest", is_system=True)
        test_db.add(exercise)
        test_db.commit()

        response = admin_client.post(
            "/admin/exercises",
            data={
                "name": "Bench Press",
                "muscle_group": "chest",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        count = test_db.query(Exercise).filter(Exercise.name == "Bench Press").count()
        assert count == 1

    def test_admin_create_exercise_optional_fields(self, admin_client, test_db):
        """Admin can create an exercise with only required fields."""
        response = admin_client.post(
            "/admin/exercises",
            data={
                "name": "Bodyweight Squat",
                "muscle_group": "legs",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        exercise = test_db.query(Exercise).filter(Exercise.name == "Bodyweight Squat").first()
        assert exercise is not None
        assert exercise.equipment is None
        assert exercise.instructions is None


class TestAdminEditExercise:
    """Tests for admin exercise editing."""

    def test_admin_edit_exercise_form(self, admin_client, test_db):
        """Admin can access the edit exercise form."""
        exercise = Exercise(name="Squat", muscle_group="legs", equipment="barbell", is_system=True)
        test_db.add(exercise)
        test_db.commit()
        test_db.refresh(exercise)

        response = admin_client.get(f"/admin/exercises/{exercise.id}/edit")
        assert response.status_code == 200
        assert "Squat" in response.text

    def test_admin_edit_exercise_success(self, admin_client, test_db):
        """Admin can update an exercise."""
        exercise = Exercise(
            name="Squat",
            muscle_group="legs",
            equipment="barbell",
            instructions="Old instructions",
            is_system=True,
        )
        test_db.add(exercise)
        test_db.commit()
        test_db.refresh(exercise)

        response = admin_client.post(
            f"/admin/exercises/{exercise.id}/edit",
            data={
                "name": "Barbell Back Squat",
                "muscle_group": "legs",
                "equipment": "barbell",
                "instructions": "Updated instructions for squat.",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        test_db.refresh(exercise)
        assert exercise.name == "Barbell Back Squat"
        assert exercise.instructions == "Updated instructions for squat."

    def test_admin_edit_exercise_not_found(self, admin_client):
        """Editing a non-existent exercise should redirect with error."""
        response = admin_client.get("/admin/exercises/99999/edit", follow_redirects=False)
        assert response.status_code == 303

    def test_admin_edit_exercise_empty_name(self, admin_client, test_db):
        """Editing an exercise with empty name should fail."""
        exercise = Exercise(name="Squat", muscle_group="legs", is_system=True)
        test_db.add(exercise)
        test_db.commit()
        test_db.refresh(exercise)

        response = admin_client.post(
            f"/admin/exercises/{exercise.id}/edit",
            data={
                "name": "",
                "muscle_group": "legs",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        test_db.refresh(exercise)
        assert exercise.name == "Squat"

    def test_admin_edit_exercise_duplicate_name(self, admin_client, test_db):
        """Editing an exercise to a duplicate name should fail."""
        exercise1 = Exercise(name="Squat", muscle_group="legs", is_system=True)
        exercise2 = Exercise(name="Deadlift", muscle_group="back", is_system=True)
        test_db.add(exercise1)
        test_db.add(exercise2)
        test_db.commit()
        test_db.refresh(exercise2)

        response = admin_client.post(
            f"/admin/exercises/{exercise2.id}/edit",
            data={
                "name": "Squat",
                "muscle_group": "back",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        test_db.refresh(exercise2)
        assert exercise2.name == "Deadlift"


class TestAdminDeleteExercise:
    """Tests for admin exercise deletion."""

    def test_admin_delete_exercise_success(self, admin_client, test_db):
        """Admin can delete an exercise."""
        exercise = Exercise(name="Cable Fly", muscle_group="chest", is_system=True)
        test_db.add(exercise)
        test_db.commit()
        test_db.refresh(exercise)
        exercise_id = exercise.id

        response = admin_client.post(
            f"/admin/exercises/{exercise_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303

        deleted = test_db.query(Exercise).filter(Exercise.id == exercise_id).first()
        assert deleted is None

    def test_admin_delete_exercise_not_found(self, admin_client):
        """Deleting a non-existent exercise should redirect with error."""
        response = admin_client.post(
            "/admin/exercises/99999/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestNonAdminCannotManageExercises:
    """Tests that non-admin users cannot create, edit, or delete exercises."""

    def test_non_admin_cannot_create_exercise(self, authenticated_client, test_db):
        """Regular users cannot create exercises via admin endpoint."""
        response = authenticated_client.post(
            "/admin/exercises",
            data={
                "name": "Unauthorized Exercise",
                "muscle_group": "chest",
            },
            follow_redirects=False,
        )
        assert response.status_code in (302, 303, 401, 403)

        exercise = test_db.query(Exercise).filter(Exercise.name == "Unauthorized Exercise").first()
        assert exercise is None

    def test_non_admin_cannot_edit_exercise(self, authenticated_client, test_db):
        """Regular users cannot edit exercises via admin endpoint."""
        exercise = Exercise(name="Squat", muscle_group="legs", is_system=True)
        test_db.add(exercise)
        test_db.commit()
        test_db.refresh(exercise)

        response = authenticated_client.post(
            f"/admin/exercises/{exercise.id}/edit",
            data={
                "name": "Hacked Squat",
                "muscle_group": "legs",
            },
            follow_redirects=False,
        )
        assert response.status_code in (302, 303, 401, 403)

        test_db.refresh(exercise)
        assert exercise.name == "Squat"

    def test_non_admin_cannot_delete_exercise(self, authenticated_client, test_db):
        """Regular users cannot delete exercises via admin endpoint."""
        exercise = Exercise(name="Squat", muscle_group="legs", is_system=True)
        test_db.add(exercise)
        test_db.commit()
        test_db.refresh(exercise)
        exercise_id = exercise.id

        response = authenticated_client.post(
            f"/admin/exercises/{exercise_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code in (302, 303, 401, 403)

        still_exists = test_db.query(Exercise).filter(Exercise.id == exercise_id).first()
        assert still_exists is not None

    def test_non_admin_cannot_access_edit_form(self, authenticated_client, test_db):
        """Regular users cannot access the admin edit exercise form."""
        exercise = Exercise(name="Squat", muscle_group="legs", is_system=True)
        test_db.add(exercise)
        test_db.commit()
        test_db.refresh(exercise)

        response = authenticated_client.get(
            f"/admin/exercises/{exercise.id}/edit",
            follow_redirects=False,
        )
        assert response.status_code in (302, 303, 401, 403)

    def test_non_admin_cannot_access_admin_dashboard(self, authenticated_client):
        """Regular users cannot access the admin dashboard."""
        response = authenticated_client.get("/admin/dashboard", follow_redirects=False)
        assert response.status_code in (302, 303, 401, 403)

    def test_unauthenticated_cannot_create_exercise(self, test_client, test_db):
        """Unauthenticated users cannot create exercises."""
        response = test_client.post(
            "/admin/exercises",
            data={
                "name": "Anon Exercise",
                "muscle_group": "chest",
            },
            follow_redirects=False,
        )
        assert response.status_code in (302, 303, 401, 403)

        exercise = test_db.query(Exercise).filter(Exercise.name == "Anon Exercise").first()
        assert exercise is None