import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal
from models.exercise import Exercise
from models.workout import Workout
from models.workout_exercise import WorkoutExercise
from models.exercise_set import ExerciseSet
from models.personal_record import PersonalRecord
from utils.security import hash_password, create_access_token


def _create_exercises(db):
    """Create sample exercises and return them."""
    exercises = []
    exercise_data = [
        {"name": "Bench Press", "muscle_group": "chest", "equipment": "barbell", "is_system": True},
        {"name": "Squat", "muscle_group": "legs", "equipment": "barbell", "is_system": True},
        {"name": "Pull-Up", "muscle_group": "back", "equipment": "bodyweight", "is_system": True},
    ]
    for data in exercise_data:
        ex = Exercise(**data)
        db.add(ex)
    db.commit()
    for data in exercise_data:
        ex = db.query(Exercise).filter(Exercise.name == data["name"]).first()
        exercises.append(ex)
    return exercises


def _build_workout_form_data(name, workout_date, exercises_data, duration_minutes=None, notes=""):
    """Build form data dict for workout creation/edit."""
    form = {
        "name": name,
        "workout_date": workout_date,
        "duration_minutes": str(duration_minutes) if duration_minutes else "",
        "notes": notes,
    }
    for ex_idx, ex_data in enumerate(exercises_data):
        form[f"exercises[{ex_idx}][exercise_id]"] = str(ex_data["exercise_id"])
        form[f"exercises[{ex_idx}][sort_order]"] = str(ex_idx + 1)
        form[f"exercises[{ex_idx}][notes]"] = ex_data.get("notes", "")
        for set_idx, set_data in enumerate(ex_data.get("sets", [])):
            form[f"exercises[{ex_idx}][sets][{set_idx}][set_number]"] = str(set_idx + 1)
            form[f"exercises[{ex_idx}][sets][{set_idx}][weight]"] = str(set_data.get("weight", ""))
            form[f"exercises[{ex_idx}][sets][{set_idx}][reps]"] = str(set_data.get("reps", ""))
    return form


class TestCreateWorkout:
    """Tests for creating a new workout."""

    def test_create_workout_success(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        form_data = _build_workout_form_data(
            name="Push Day",
            workout_date=date.today().isoformat(),
            duration_minutes=60,
            notes="Great session",
            exercises_data=[
                {
                    "exercise_id": exercises[0].id,
                    "sets": [
                        {"weight": 60.0, "reps": 8},
                        {"weight": 65.0, "reps": 6},
                    ],
                },
            ],
        )

        response = authenticated_client.post("/workouts/new", data=form_data, follow_redirects=False)

        assert response.status_code == 302
        assert "/workouts/" in response.headers["location"]

        workout = test_db.query(Workout).filter(Workout.user_id == test_user.id).first()
        assert workout is not None
        assert workout.name == "Push Day"
        assert workout.duration_minutes == 60
        assert workout.notes == "Great session"

    def test_create_workout_multiple_exercises(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        form_data = _build_workout_form_data(
            name="Full Body",
            workout_date=date.today().isoformat(),
            exercises_data=[
                {
                    "exercise_id": exercises[0].id,
                    "sets": [{"weight": 60.0, "reps": 8}],
                },
                {
                    "exercise_id": exercises[1].id,
                    "sets": [{"weight": 100.0, "reps": 5}],
                },
                {
                    "exercise_id": exercises[2].id,
                    "sets": [{"weight": 0, "reps": 10}],
                },
            ],
        )

        response = authenticated_client.post("/workouts/new", data=form_data, follow_redirects=False)

        assert response.status_code == 302

        workout = test_db.query(Workout).filter(Workout.user_id == test_user.id).first()
        assert workout is not None

        workout_exercises = test_db.query(WorkoutExercise).filter(
            WorkoutExercise.workout_id == workout.id
        ).all()
        assert len(workout_exercises) == 3

    def test_create_workout_missing_name_returns_error(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        form_data = _build_workout_form_data(
            name="",
            workout_date=date.today().isoformat(),
            exercises_data=[
                {
                    "exercise_id": exercises[0].id,
                    "sets": [{"weight": 60.0, "reps": 8}],
                },
            ],
        )

        response = authenticated_client.post("/workouts/new", data=form_data, follow_redirects=False)

        assert response.status_code == 200
        workout_count = test_db.query(Workout).filter(Workout.user_id == test_user.id).count()
        assert workout_count == 0

    def test_create_workout_no_exercises_returns_error(self, authenticated_client, test_user, test_db):
        form_data = {
            "name": "Empty Workout",
            "workout_date": date.today().isoformat(),
            "duration_minutes": "",
            "notes": "",
        }

        response = authenticated_client.post("/workouts/new", data=form_data, follow_redirects=False)

        assert response.status_code == 200
        workout_count = test_db.query(Workout).filter(Workout.user_id == test_user.id).count()
        assert workout_count == 0

    def test_create_workout_requires_authentication(self, test_client, test_db):
        exercises = _create_exercises(test_db)
        form_data = _build_workout_form_data(
            name="Unauthorized Workout",
            workout_date=date.today().isoformat(),
            exercises_data=[
                {
                    "exercise_id": exercises[0].id,
                    "sets": [{"weight": 60.0, "reps": 8}],
                },
            ],
        )

        response = test_client.post("/workouts/new", data=form_data, follow_redirects=False)

        assert response.status_code in (401, 302, 303)

    def test_create_workout_with_multiple_sets(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        form_data = _build_workout_form_data(
            name="Heavy Bench",
            workout_date=date.today().isoformat(),
            duration_minutes=45,
            exercises_data=[
                {
                    "exercise_id": exercises[0].id,
                    "sets": [
                        {"weight": 60.0, "reps": 10},
                        {"weight": 70.0, "reps": 8},
                        {"weight": 80.0, "reps": 6},
                        {"weight": 85.0, "reps": 4},
                    ],
                },
            ],
        )

        response = authenticated_client.post("/workouts/new", data=form_data, follow_redirects=False)

        assert response.status_code == 302

        workout = test_db.query(Workout).filter(Workout.user_id == test_user.id).first()
        assert workout is not None

        we = test_db.query(WorkoutExercise).filter(
            WorkoutExercise.workout_id == workout.id
        ).first()
        assert we is not None

        sets = test_db.query(ExerciseSet).filter(
            ExerciseSet.workout_exercise_id == we.id
        ).all()
        assert len(sets) == 4


class TestEditWorkout:
    """Tests for editing an existing workout."""

    def _create_workout(self, db, user_id, exercises):
        """Helper to create a workout directly in the DB."""
        workout = Workout(
            user_id=user_id,
            name="Original Workout",
            workout_date=date.today(),
            duration_minutes=30,
            notes="Original notes",
        )
        db.add(workout)
        db.flush()

        we = WorkoutExercise(
            workout_id=workout.id,
            exercise_id=exercises[0].id,
            sort_order=1,
            notes="",
        )
        db.add(we)
        db.flush()

        exercise_set = ExerciseSet(
            workout_exercise_id=we.id,
            set_number=1,
            weight=50.0,
            reps=10,
            is_completed=True,
            is_pr=False,
        )
        db.add(exercise_set)
        db.commit()
        db.refresh(workout)
        return workout

    def test_edit_workout_success(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        workout = self._create_workout(test_db, test_user.id, exercises)

        form_data = _build_workout_form_data(
            name="Updated Workout",
            workout_date=date.today().isoformat(),
            duration_minutes=90,
            notes="Updated notes",
            exercises_data=[
                {
                    "exercise_id": exercises[0].id,
                    "sets": [
                        {"weight": 70.0, "reps": 8},
                        {"weight": 75.0, "reps": 6},
                    ],
                },
            ],
        )

        response = authenticated_client.post(
            f"/workouts/{workout.id}/edit", data=form_data, follow_redirects=False
        )

        assert response.status_code == 302

        test_db.refresh(workout)
        assert workout.name == "Updated Workout"
        assert workout.duration_minutes == 90
        assert workout.notes == "Updated notes"

    def test_edit_workout_get_form(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        workout = self._create_workout(test_db, test_user.id, exercises)

        response = authenticated_client.get(f"/workouts/{workout.id}/edit")

        assert response.status_code == 200
        assert "Original Workout" in response.text

    def test_edit_workout_missing_name(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        workout = self._create_workout(test_db, test_user.id, exercises)

        form_data = _build_workout_form_data(
            name="",
            workout_date=date.today().isoformat(),
            exercises_data=[
                {
                    "exercise_id": exercises[0].id,
                    "sets": [{"weight": 60.0, "reps": 8}],
                },
            ],
        )

        response = authenticated_client.post(
            f"/workouts/{workout.id}/edit", data=form_data, follow_redirects=False
        )

        assert response.status_code == 200

        test_db.refresh(workout)
        assert workout.name == "Original Workout"

    def test_edit_nonexistent_workout_redirects(self, authenticated_client, test_db):
        response = authenticated_client.get("/workouts/99999/edit", follow_redirects=False)

        assert response.status_code == 302
        assert "/workouts/history" in response.headers["location"]


class TestDeleteWorkout:
    """Tests for deleting a workout."""

    def _create_workout(self, db, user_id, exercises):
        workout = Workout(
            user_id=user_id,
            name="Workout to Delete",
            workout_date=date.today(),
            duration_minutes=30,
            notes="",
        )
        db.add(workout)
        db.flush()

        we = WorkoutExercise(
            workout_id=workout.id,
            exercise_id=exercises[0].id,
            sort_order=1,
            notes="",
        )
        db.add(we)
        db.flush()

        exercise_set = ExerciseSet(
            workout_exercise_id=we.id,
            set_number=1,
            weight=50.0,
            reps=10,
            is_completed=True,
            is_pr=False,
        )
        db.add(exercise_set)
        db.commit()
        db.refresh(workout)
        return workout

    def test_delete_workout_success(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        workout = self._create_workout(test_db, test_user.id, exercises)
        workout_id = workout.id

        response = authenticated_client.post(
            f"/workouts/{workout_id}/delete", follow_redirects=False
        )

        assert response.status_code == 302
        assert "/workouts/history" in response.headers["location"]

        deleted = test_db.query(Workout).filter(Workout.id == workout_id).first()
        assert deleted is None

    def test_delete_nonexistent_workout(self, authenticated_client, test_db):
        response = authenticated_client.post(
            "/workouts/99999/delete", follow_redirects=False
        )

        assert response.status_code == 302
        assert "/workouts/history" in response.headers["location"]

    def test_delete_workout_cascades_exercises_and_sets(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        workout = self._create_workout(test_db, test_user.id, exercises)
        workout_id = workout.id

        we_count_before = test_db.query(WorkoutExercise).filter(
            WorkoutExercise.workout_id == workout_id
        ).count()
        assert we_count_before > 0

        response = authenticated_client.post(
            f"/workouts/{workout_id}/delete", follow_redirects=False
        )

        assert response.status_code == 302

        we_count_after = test_db.query(WorkoutExercise).filter(
            WorkoutExercise.workout_id == workout_id
        ).count()
        assert we_count_after == 0


class TestWorkoutOwnership:
    """Tests for workout ownership enforcement."""

    def _create_workout_for_user(self, db, user_id, exercises):
        workout = Workout(
            user_id=user_id,
            name="Other User Workout",
            workout_date=date.today(),
            duration_minutes=30,
            notes="",
        )
        db.add(workout)
        db.flush()

        we = WorkoutExercise(
            workout_id=workout.id,
            exercise_id=exercises[0].id,
            sort_order=1,
            notes="",
        )
        db.add(we)
        db.flush()

        exercise_set = ExerciseSet(
            workout_exercise_id=we.id,
            set_number=1,
            weight=50.0,
            reps=10,
            is_completed=True,
            is_pr=False,
        )
        db.add(exercise_set)
        db.commit()
        db.refresh(workout)
        return workout

    def test_cannot_view_other_users_workout(self, authenticated_client, test_user, admin_user, test_db):
        exercises = _create_exercises(test_db)
        other_workout = self._create_workout_for_user(test_db, admin_user.id, exercises)

        response = authenticated_client.get(
            f"/workouts/{other_workout.id}", follow_redirects=False
        )

        assert response.status_code == 302
        assert "/workouts/history" in response.headers["location"]

    def test_cannot_edit_other_users_workout(self, authenticated_client, test_user, admin_user, test_db):
        exercises = _create_exercises(test_db)
        other_workout = self._create_workout_for_user(test_db, admin_user.id, exercises)

        response = authenticated_client.get(
            f"/workouts/{other_workout.id}/edit", follow_redirects=False
        )

        assert response.status_code == 302
        assert "/workouts/history" in response.headers["location"]

    def test_cannot_delete_other_users_workout(self, authenticated_client, test_user, admin_user, test_db):
        exercises = _create_exercises(test_db)
        other_workout = self._create_workout_for_user(test_db, admin_user.id, exercises)
        workout_id = other_workout.id

        response = authenticated_client.post(
            f"/workouts/{workout_id}/delete", follow_redirects=False
        )

        assert response.status_code == 302

        still_exists = test_db.query(Workout).filter(Workout.id == workout_id).first()
        assert still_exists is not None

    def test_cannot_post_edit_other_users_workout(self, authenticated_client, test_user, admin_user, test_db):
        exercises = _create_exercises(test_db)
        other_workout = self._create_workout_for_user(test_db, admin_user.id, exercises)

        form_data = _build_workout_form_data(
            name="Hacked Workout",
            workout_date=date.today().isoformat(),
            exercises_data=[
                {
                    "exercise_id": exercises[0].id,
                    "sets": [{"weight": 999.0, "reps": 999}],
                },
            ],
        )

        response = authenticated_client.post(
            f"/workouts/{other_workout.id}/edit", data=form_data, follow_redirects=False
        )

        assert response.status_code == 302

        test_db.refresh(other_workout)
        assert other_workout.name == "Other User Workout"


class TestPRDetection:
    """Tests for personal record detection on workout save."""

    def test_pr_detected_on_first_workout(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        form_data = _build_workout_form_data(
            name="First Workout",
            workout_date=date.today().isoformat(),
            exercises_data=[
                {
                    "exercise_id": exercises[0].id,
                    "sets": [
                        {"weight": 80.0, "reps": 5},
                    ],
                },
            ],
        )

        response = authenticated_client.post("/workouts/new", data=form_data, follow_redirects=False)

        assert response.status_code == 302

        prs = test_db.query(PersonalRecord).filter(
            PersonalRecord.user_id == test_user.id,
            PersonalRecord.exercise_id == exercises[0].id,
        ).all()

        assert len(prs) > 0

        pr_types = {pr.record_type for pr in prs}
        assert "weight" in pr_types

    def test_pr_updated_when_new_record_set(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)

        form_data_1 = _build_workout_form_data(
            name="Workout 1",
            workout_date=(date.today() - timedelta(days=1)).isoformat(),
            exercises_data=[
                {
                    "exercise_id": exercises[0].id,
                    "sets": [{"weight": 60.0, "reps": 8}],
                },
            ],
        )
        authenticated_client.post("/workouts/new", data=form_data_1, follow_redirects=False)

        weight_pr = test_db.query(PersonalRecord).filter(
            PersonalRecord.user_id == test_user.id,
            PersonalRecord.exercise_id == exercises[0].id,
            PersonalRecord.record_type == "weight",
        ).first()
        assert weight_pr is not None
        assert weight_pr.value == 60.0

        form_data_2 = _build_workout_form_data(
            name="Workout 2",
            workout_date=date.today().isoformat(),
            exercises_data=[
                {
                    "exercise_id": exercises[0].id,
                    "sets": [{"weight": 80.0, "reps": 5}],
                },
            ],
        )
        authenticated_client.post("/workouts/new", data=form_data_2, follow_redirects=False)

        test_db.expire_all()
        weight_pr = test_db.query(PersonalRecord).filter(
            PersonalRecord.user_id == test_user.id,
            PersonalRecord.exercise_id == exercises[0].id,
            PersonalRecord.record_type == "weight",
        ).first()
        assert weight_pr is not None
        assert weight_pr.value == 80.0

    def test_pr_not_updated_when_lower_weight(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)

        form_data_1 = _build_workout_form_data(
            name="Heavy Day",
            workout_date=(date.today() - timedelta(days=1)).isoformat(),
            exercises_data=[
                {
                    "exercise_id": exercises[0].id,
                    "sets": [{"weight": 100.0, "reps": 3}],
                },
            ],
        )
        authenticated_client.post("/workouts/new", data=form_data_1, follow_redirects=False)

        form_data_2 = _build_workout_form_data(
            name="Light Day",
            workout_date=date.today().isoformat(),
            exercises_data=[
                {
                    "exercise_id": exercises[0].id,
                    "sets": [{"weight": 60.0, "reps": 12}],
                },
            ],
        )
        authenticated_client.post("/workouts/new", data=form_data_2, follow_redirects=False)

        test_db.expire_all()
        weight_pr = test_db.query(PersonalRecord).filter(
            PersonalRecord.user_id == test_user.id,
            PersonalRecord.exercise_id == exercises[0].id,
            PersonalRecord.record_type == "weight",
        ).first()
        assert weight_pr is not None
        assert weight_pr.value == 100.0

    def test_volume_pr_detected(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        form_data = _build_workout_form_data(
            name="Volume Day",
            workout_date=date.today().isoformat(),
            exercises_data=[
                {
                    "exercise_id": exercises[0].id,
                    "sets": [{"weight": 50.0, "reps": 20}],
                },
            ],
        )

        authenticated_client.post("/workouts/new", data=form_data, follow_redirects=False)

        volume_pr = test_db.query(PersonalRecord).filter(
            PersonalRecord.user_id == test_user.id,
            PersonalRecord.exercise_id == exercises[0].id,
            PersonalRecord.record_type == "volume",
        ).first()
        assert volume_pr is not None
        assert volume_pr.value == 1000.0


class TestWorkoutHistory:
    """Tests for workout history listing."""

    def _create_workouts(self, db, user_id, exercises, count=5):
        workouts = []
        for i in range(count):
            workout = Workout(
                user_id=user_id,
                name=f"Workout {i + 1}",
                workout_date=date.today() - timedelta(days=i),
                duration_minutes=30 + i * 5,
                notes=f"Notes for workout {i + 1}",
            )
            db.add(workout)
            db.flush()

            we = WorkoutExercise(
                workout_id=workout.id,
                exercise_id=exercises[0].id,
                sort_order=1,
                notes="",
            )
            db.add(we)
            db.flush()

            exercise_set = ExerciseSet(
                workout_exercise_id=we.id,
                set_number=1,
                weight=50.0 + i * 5,
                reps=10,
                is_completed=True,
                is_pr=False,
            )
            db.add(exercise_set)
            workouts.append(workout)

        db.commit()
        for w in workouts:
            db.refresh(w)
        return workouts

    def test_workout_history_page_loads(self, authenticated_client, test_user, test_db):
        response = authenticated_client.get("/workouts/history")

        assert response.status_code == 200
        assert "Workout History" in response.text

    def test_workout_history_shows_workouts(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        self._create_workouts(test_db, test_user.id, exercises, count=3)

        response = authenticated_client.get("/workouts/history")

        assert response.status_code == 200
        assert "Workout 1" in response.text
        assert "Workout 2" in response.text
        assert "Workout 3" in response.text

    def test_workout_history_empty_state(self, authenticated_client, test_user, test_db):
        response = authenticated_client.get("/workouts/history")

        assert response.status_code == 200
        assert "No workouts this month" in response.text or "Log Workout" in response.text

    def test_workout_history_month_navigation(self, authenticated_client, test_user, test_db):
        today = date.today()
        response = authenticated_client.get(
            f"/workouts/history?year={today.year}&month={today.month}"
        )

        assert response.status_code == 200

    def test_workouts_redirect_to_history(self, authenticated_client, test_db):
        response = authenticated_client.get("/workouts", follow_redirects=False)

        assert response.status_code == 302
        assert "/workouts/history" in response.headers["location"]

    def test_workout_history_does_not_show_other_users_workouts(
        self, authenticated_client, test_user, admin_user, test_db
    ):
        exercises = _create_exercises(test_db)

        other_workout = Workout(
            user_id=admin_user.id,
            name="Admin Secret Workout",
            workout_date=date.today(),
            duration_minutes=60,
            notes="",
        )
        test_db.add(other_workout)
        test_db.flush()

        we = WorkoutExercise(
            workout_id=other_workout.id,
            exercise_id=exercises[0].id,
            sort_order=1,
            notes="",
        )
        test_db.add(we)
        test_db.flush()

        exercise_set = ExerciseSet(
            workout_exercise_id=we.id,
            set_number=1,
            weight=50.0,
            reps=10,
            is_completed=True,
            is_pr=False,
        )
        test_db.add(exercise_set)
        test_db.commit()

        response = authenticated_client.get("/workouts/history")

        assert response.status_code == 200
        assert "Admin Secret Workout" not in response.text


class TestWorkoutDetail:
    """Tests for workout detail page."""

    def _create_workout_with_details(self, db, user_id, exercises):
        workout = Workout(
            user_id=user_id,
            name="Detailed Workout",
            workout_date=date.today(),
            duration_minutes=75,
            notes="Detailed notes here",
        )
        db.add(workout)
        db.flush()

        for idx, ex in enumerate(exercises[:2]):
            we = WorkoutExercise(
                workout_id=workout.id,
                exercise_id=ex.id,
                sort_order=idx + 1,
                notes=f"Notes for exercise {idx + 1}",
            )
            db.add(we)
            db.flush()

            for set_num in range(1, 4):
                exercise_set = ExerciseSet(
                    workout_exercise_id=we.id,
                    set_number=set_num,
                    weight=50.0 + set_num * 10,
                    reps=10 - set_num,
                    is_completed=True,
                    is_pr=(set_num == 3),
                )
                db.add(exercise_set)

        db.commit()
        db.refresh(workout)
        return workout

    def test_workout_detail_page_loads(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        workout = self._create_workout_with_details(test_db, test_user.id, exercises)

        response = authenticated_client.get(f"/workouts/{workout.id}")

        assert response.status_code == 200
        assert "Detailed Workout" in response.text

    def test_workout_detail_shows_exercises(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        workout = self._create_workout_with_details(test_db, test_user.id, exercises)

        response = authenticated_client.get(f"/workouts/{workout.id}")

        assert response.status_code == 200
        assert exercises[0].name in response.text
        assert exercises[1].name in response.text

    def test_workout_detail_shows_sets(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        workout = self._create_workout_with_details(test_db, test_user.id, exercises)

        response = authenticated_client.get(f"/workouts/{workout.id}")

        assert response.status_code == 200
        assert "60" in response.text or "70" in response.text or "80" in response.text

    def test_workout_detail_shows_duration(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        workout = self._create_workout_with_details(test_db, test_user.id, exercises)

        response = authenticated_client.get(f"/workouts/{workout.id}")

        assert response.status_code == 200
        assert "75" in response.text

    def test_workout_detail_shows_notes(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        workout = self._create_workout_with_details(test_db, test_user.id, exercises)

        response = authenticated_client.get(f"/workouts/{workout.id}")

        assert response.status_code == 200
        assert "Detailed notes here" in response.text

    def test_workout_detail_shows_pr_badge(self, authenticated_client, test_user, test_db):
        exercises = _create_exercises(test_db)
        workout = self._create_workout_with_details(test_db, test_user.id, exercises)

        response = authenticated_client.get(f"/workouts/{workout.id}")

        assert response.status_code == 200
        assert "PR" in response.text

    def test_workout_detail_nonexistent_redirects(self, authenticated_client, test_db):
        response = authenticated_client.get("/workouts/99999", follow_redirects=False)

        assert response.status_code == 302
        assert "/workouts/history" in response.headers["location"]

    def test_workout_detail_shows_edit_delete_buttons_for_owner(
        self, authenticated_client, test_user, test_db
    ):
        exercises = _create_exercises(test_db)
        workout = self._create_workout_with_details(test_db, test_user.id, exercises)

        response = authenticated_client.get(f"/workouts/{workout.id}")

        assert response.status_code == 200
        assert "Edit" in response.text
        assert "Delete" in response.text


class TestNewWorkoutForm:
    """Tests for the new workout form page."""

    def test_new_workout_form_loads(self, authenticated_client, test_db):
        _create_exercises(test_db)

        response = authenticated_client.get("/workouts/new")

        assert response.status_code == 200
        assert "Log New Workout" in response.text

    def test_new_workout_form_shows_exercises(self, authenticated_client, test_db):
        exercises = _create_exercises(test_db)

        response = authenticated_client.get("/workouts/new")

        assert response.status_code == 200
        for ex in exercises:
            assert ex.name in response.text

    def test_new_workout_form_requires_auth(self, test_client, test_db):
        response = test_client.get("/workouts/new", follow_redirects=False)

        assert response.status_code in (401, 302, 303)