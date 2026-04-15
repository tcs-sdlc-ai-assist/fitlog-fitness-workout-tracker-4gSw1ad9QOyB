import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from tests.conftest import *
from models.exercise import Exercise
from models.workout import Workout
from models.workout_exercise import WorkoutExercise
from models.exercise_set import ExerciseSet
from models.personal_record import PersonalRecord
from models.body_measurement import BodyMeasurement
from services.pr_service import PRService
from services.progress_service import ProgressService
from services.workout_service import (
    get_current_streak,
    get_longest_streak,
    get_weekly_average,
    get_workouts_this_month,
    get_total_workout_count,
)


def _create_exercise(db, name="Bench Press", muscle_group="chest", equipment="barbell"):
    exercise = Exercise(
        name=name,
        muscle_group=muscle_group,
        equipment=equipment,
        instructions="Test instructions",
        is_system=True,
    )
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise


def _create_workout(db, user_id, name="Test Workout", workout_date=None):
    if workout_date is None:
        workout_date = date.today()
    workout = Workout(
        user_id=user_id,
        name=name,
        workout_date=workout_date,
        duration_minutes=60,
        notes="Test workout",
    )
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return workout


def _create_workout_exercise(db, workout_id, exercise_id, sort_order=1):
    we = WorkoutExercise(
        workout_id=workout_id,
        exercise_id=exercise_id,
        sort_order=sort_order,
        notes="",
    )
    db.add(we)
    db.commit()
    db.refresh(we)
    return we


def _create_set(db, workout_exercise_id, set_number=1, weight=60.0, reps=8):
    s = ExerciseSet(
        workout_exercise_id=workout_exercise_id,
        set_number=set_number,
        weight=weight,
        reps=reps,
        is_completed=True,
        is_pr=False,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _create_personal_record(db, user_id, exercise_id, record_type="weight", value=100.0, achieved_at=None):
    from datetime import datetime
    if achieved_at is None:
        achieved_at = datetime.utcnow()
    pr = PersonalRecord(
        user_id=user_id,
        exercise_id=exercise_id,
        record_type=record_type,
        value=value,
        achieved_at=achieved_at,
    )
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr


class TestProgressPage:
    """Tests for the progress page rendering."""

    def test_progress_page_requires_auth(self, test_client):
        response = test_client.get("/progress", follow_redirects=False)
        assert response.status_code in (401, 302, 303)

    def test_progress_page_renders_for_authenticated_user(self, authenticated_client):
        response = authenticated_client.get("/progress", follow_redirects=False)
        assert response.status_code == 200
        assert b"Progress" in response.content

    def test_progress_page_shows_empty_state(self, authenticated_client):
        response = authenticated_client.get("/progress")
        assert response.status_code == 200
        assert b"Current Streak" in response.content
        assert b"Longest Streak" in response.content
        assert b"Weekly Average" in response.content

    def test_progress_page_shows_consistency_stats(self, authenticated_client, test_user, test_db):
        exercise = _create_exercise(test_db)
        workout = _create_workout(test_db, test_user.id, workout_date=date.today())
        we = _create_workout_exercise(test_db, workout.id, exercise.id)
        _create_set(test_db, we.id)

        response = authenticated_client.get("/progress")
        assert response.status_code == 200
        assert b"Current Streak" in response.content
        assert b"This Month" in response.content

    def test_progress_page_shows_muscle_group_distribution(self, authenticated_client, test_user, test_db):
        exercise_chest = _create_exercise(test_db, name="Bench Press", muscle_group="chest")
        exercise_back = _create_exercise(test_db, name="Deadlift", muscle_group="back")

        workout = _create_workout(test_db, test_user.id)
        we1 = _create_workout_exercise(test_db, workout.id, exercise_chest.id, sort_order=1)
        we2 = _create_workout_exercise(test_db, workout.id, exercise_back.id, sort_order=2)
        _create_set(test_db, we1.id, set_number=1, weight=80, reps=8)
        _create_set(test_db, we1.id, set_number=2, weight=80, reps=8)
        _create_set(test_db, we2.id, set_number=1, weight=100, reps=5)

        response = authenticated_client.get("/progress")
        assert response.status_code == 200
        assert b"Muscle Group Distribution" in response.content

    def test_progress_page_shows_personal_records(self, authenticated_client, test_user, test_db):
        from datetime import datetime
        exercise = _create_exercise(test_db)
        _create_personal_record(
            test_db,
            test_user.id,
            exercise.id,
            record_type="weight",
            value=100.0,
            achieved_at=datetime.utcnow(),
        )

        response = authenticated_client.get("/progress")
        assert response.status_code == 200
        assert b"Personal Records" in response.content


class TestPRService:
    """Tests for the PRService personal record detection and retrieval."""

    def test_detect_prs_creates_new_weight_pr(self, test_db, test_user):
        exercise = _create_exercise(test_db)
        pr_service = PRService(test_db)

        sets_data = [
            {"weight": 80.0, "reps": 8},
            {"weight": 100.0, "reps": 5},
        ]

        new_prs = pr_service.detect_prs(
            user_id=test_user.id,
            exercise_id=exercise.id,
            sets=sets_data,
            workout_date=date.today(),
        )
        test_db.commit()

        assert len(new_prs) > 0
        weight_prs = [pr for pr in new_prs if pr.record_type == "weight"]
        assert len(weight_prs) == 1
        assert weight_prs[0].value == 100.0

    def test_detect_prs_creates_reps_pr(self, test_db, test_user):
        exercise = _create_exercise(test_db)
        pr_service = PRService(test_db)

        sets_data = [
            {"weight": 60.0, "reps": 12},
            {"weight": 60.0, "reps": 15},
        ]

        new_prs = pr_service.detect_prs(
            user_id=test_user.id,
            exercise_id=exercise.id,
            sets=sets_data,
            workout_date=date.today(),
        )
        test_db.commit()

        reps_prs = [pr for pr in new_prs if pr.record_type == "reps"]
        assert len(reps_prs) == 1
        assert reps_prs[0].value == 15.0

    def test_detect_prs_creates_volume_pr(self, test_db, test_user):
        exercise = _create_exercise(test_db)
        pr_service = PRService(test_db)

        sets_data = [
            {"weight": 80.0, "reps": 10},
        ]

        new_prs = pr_service.detect_prs(
            user_id=test_user.id,
            exercise_id=exercise.id,
            sets=sets_data,
            workout_date=date.today(),
        )
        test_db.commit()

        volume_prs = [pr for pr in new_prs if pr.record_type == "volume"]
        assert len(volume_prs) == 1
        assert volume_prs[0].value == 800.0

    def test_detect_prs_updates_existing_pr_when_higher(self, test_db, test_user):
        exercise = _create_exercise(test_db)
        pr_service = PRService(test_db)

        sets_data_1 = [{"weight": 80.0, "reps": 8}]
        pr_service.detect_prs(
            user_id=test_user.id,
            exercise_id=exercise.id,
            sets=sets_data_1,
            workout_date=date.today() - timedelta(days=7),
        )
        test_db.commit()

        sets_data_2 = [{"weight": 100.0, "reps": 8}]
        new_prs = pr_service.detect_prs(
            user_id=test_user.id,
            exercise_id=exercise.id,
            sets=sets_data_2,
            workout_date=date.today(),
        )
        test_db.commit()

        weight_prs = [pr for pr in new_prs if pr.record_type == "weight"]
        assert len(weight_prs) == 1
        assert weight_prs[0].value == 100.0

    def test_detect_prs_does_not_update_when_lower(self, test_db, test_user):
        exercise = _create_exercise(test_db)
        pr_service = PRService(test_db)

        sets_data_1 = [{"weight": 100.0, "reps": 8}]
        pr_service.detect_prs(
            user_id=test_user.id,
            exercise_id=exercise.id,
            sets=sets_data_1,
            workout_date=date.today() - timedelta(days=7),
        )
        test_db.commit()

        sets_data_2 = [{"weight": 80.0, "reps": 6}]
        new_prs = pr_service.detect_prs(
            user_id=test_user.id,
            exercise_id=exercise.id,
            sets=sets_data_2,
            workout_date=date.today(),
        )
        test_db.commit()

        weight_prs = [pr for pr in new_prs if pr.record_type == "weight"]
        assert len(weight_prs) == 0

    def test_detect_prs_idempotent(self, test_db, test_user):
        exercise = _create_exercise(test_db)
        pr_service = PRService(test_db)

        sets_data = [{"weight": 100.0, "reps": 8}]

        pr_service.detect_prs(
            user_id=test_user.id,
            exercise_id=exercise.id,
            sets=sets_data,
            workout_date=date.today(),
        )
        test_db.commit()

        prs_again = pr_service.detect_prs(
            user_id=test_user.id,
            exercise_id=exercise.id,
            sets=sets_data,
            workout_date=date.today(),
        )
        test_db.commit()

        weight_prs = [pr for pr in prs_again if pr.record_type == "weight"]
        assert len(weight_prs) == 0

        all_prs = pr_service.get_exercise_prs(test_user.id, exercise.id)
        weight_records = [pr for pr in all_prs if pr.record_type == "weight"]
        assert len(weight_records) == 1
        assert weight_records[0].value == 100.0

    def test_get_user_prs_returns_all_prs(self, test_db, test_user):
        exercise1 = _create_exercise(test_db, name="Bench Press", muscle_group="chest")
        exercise2 = _create_exercise(test_db, name="Squat", muscle_group="legs")

        _create_personal_record(test_db, test_user.id, exercise1.id, "weight", 100.0)
        _create_personal_record(test_db, test_user.id, exercise2.id, "weight", 140.0)

        pr_service = PRService(test_db)
        all_prs = pr_service.get_user_prs(test_user.id)

        assert len(all_prs) == 2

    def test_get_exercise_prs_returns_prs_for_specific_exercise(self, test_db, test_user):
        exercise1 = _create_exercise(test_db, name="Bench Press", muscle_group="chest")
        exercise2 = _create_exercise(test_db, name="Squat", muscle_group="legs")

        _create_personal_record(test_db, test_user.id, exercise1.id, "weight", 100.0)
        _create_personal_record(test_db, test_user.id, exercise1.id, "reps", 15.0)
        _create_personal_record(test_db, test_user.id, exercise2.id, "weight", 140.0)

        pr_service = PRService(test_db)
        prs = pr_service.get_exercise_prs(test_user.id, exercise1.id)

        assert len(prs) == 2
        record_types = {pr.record_type for pr in prs}
        assert "weight" in record_types
        assert "reps" in record_types

    def test_get_exercise_prs_map(self, test_db, test_user):
        exercise1 = _create_exercise(test_db, name="Bench Press", muscle_group="chest")
        exercise2 = _create_exercise(test_db, name="Squat", muscle_group="legs")

        _create_personal_record(test_db, test_user.id, exercise1.id, "weight", 100.0)
        _create_personal_record(test_db, test_user.id, exercise2.id, "weight", 140.0)

        pr_service = PRService(test_db)
        pr_map = pr_service.get_exercise_prs_map(test_user.id)

        assert exercise1.id in pr_map
        assert exercise2.id in pr_map
        assert pr_map[exercise1.id]["weight"] == 100.0
        assert pr_map[exercise2.id]["weight"] == 140.0

    def test_get_user_prs_empty_for_new_user(self, test_db, test_user):
        pr_service = PRService(test_db)
        prs = pr_service.get_user_prs(test_user.id)
        assert len(prs) == 0


class TestRecentPRsFilter:
    """Tests for filtering recent PRs by date range."""

    def test_get_recent_prs_within_30_days(self, test_db, test_user):
        from datetime import datetime
        exercise = _create_exercise(test_db)

        recent_date = datetime.utcnow() - timedelta(days=5)
        _create_personal_record(
            test_db, test_user.id, exercise.id, "weight", 100.0, achieved_at=recent_date
        )

        pr_service = PRService(test_db)
        recent_prs = pr_service.get_recent_prs(test_user.id, days=30)

        assert len(recent_prs) == 1
        assert recent_prs[0].value == 100.0

    def test_get_recent_prs_excludes_old_prs(self, test_db, test_user):
        from datetime import datetime
        exercise = _create_exercise(test_db)

        old_date = datetime.utcnow() - timedelta(days=60)
        _create_personal_record(
            test_db, test_user.id, exercise.id, "weight", 100.0, achieved_at=old_date
        )

        pr_service = PRService(test_db)
        recent_prs = pr_service.get_recent_prs(test_user.id, days=30)

        assert len(recent_prs) == 0

    def test_get_recent_prs_with_exercise_names(self, test_db, test_user):
        from datetime import datetime
        exercise = _create_exercise(test_db, name="Barbell Bench Press")

        recent_date = datetime.utcnow() - timedelta(days=3)
        _create_personal_record(
            test_db, test_user.id, exercise.id, "weight", 100.0, achieved_at=recent_date
        )

        pr_service = PRService(test_db)
        results = pr_service.get_recent_prs_with_exercise_names(test_user.id, days=30)

        assert len(results) == 1
        assert results[0]["exercise_name"] == "Barbell Bench Press"
        assert results[0]["record_type"] == "weight"
        assert results[0]["value"] == 100.0

    def test_get_recent_prs_custom_days_filter(self, test_db, test_user):
        from datetime import datetime
        exercise = _create_exercise(test_db)

        date_8_days_ago = datetime.utcnow() - timedelta(days=8)
        _create_personal_record(
            test_db, test_user.id, exercise.id, "weight", 100.0, achieved_at=date_8_days_ago
        )

        pr_service = PRService(test_db)

        recent_7 = pr_service.get_recent_prs(test_user.id, days=7)
        assert len(recent_7) == 0

        recent_10 = pr_service.get_recent_prs(test_user.id, days=10)
        assert len(recent_10) == 1

    def test_get_all_prs_with_exercise_names(self, test_db, test_user):
        from datetime import datetime
        exercise1 = _create_exercise(test_db, name="Bench Press", muscle_group="chest")
        exercise2 = _create_exercise(test_db, name="Squat", muscle_group="legs")

        _create_personal_record(test_db, test_user.id, exercise1.id, "weight", 100.0)
        _create_personal_record(test_db, test_user.id, exercise1.id, "reps", 12.0)
        _create_personal_record(test_db, test_user.id, exercise2.id, "weight", 140.0)
        _create_personal_record(test_db, test_user.id, exercise2.id, "volume", 1400.0)

        pr_service = PRService(test_db)
        all_prs = pr_service.get_all_prs_with_exercise_names(test_user.id)

        assert len(all_prs) == 2

        exercise_names = {pr["exercise_name"] for pr in all_prs}
        assert "Bench Press" in exercise_names
        assert "Squat" in exercise_names

        bench_pr = next(pr for pr in all_prs if pr["exercise_name"] == "Bench Press")
        assert bench_pr["best_weight"] == 100.0
        assert bench_pr["best_reps"] == 12.0

        squat_pr = next(pr for pr in all_prs if pr["exercise_name"] == "Squat")
        assert squat_pr["best_weight"] == 140.0
        assert squat_pr["best_volume"] == 1400.0


class TestConsistencyStats:
    """Tests for streak calculation and consistency statistics."""

    def test_current_streak_no_workouts(self, test_db, test_user):
        streak = get_current_streak(test_db, test_user.id)
        assert streak == 0

    def test_current_streak_workout_today(self, test_db, test_user):
        _create_workout(test_db, test_user.id, workout_date=date.today())

        streak = get_current_streak(test_db, test_user.id)
        assert streak == 1

    def test_current_streak_consecutive_days(self, test_db, test_user):
        today = date.today()
        for i in range(5):
            _create_workout(
                test_db,
                test_user.id,
                name=f"Workout {i}",
                workout_date=today - timedelta(days=i),
            )

        streak = get_current_streak(test_db, test_user.id)
        assert streak == 5

    def test_current_streak_broken_by_gap(self, test_db, test_user):
        today = date.today()
        _create_workout(test_db, test_user.id, name="Today", workout_date=today)
        _create_workout(test_db, test_user.id, name="Yesterday", workout_date=today - timedelta(days=1))
        _create_workout(test_db, test_user.id, name="Old", workout_date=today - timedelta(days=5))

        streak = get_current_streak(test_db, test_user.id)
        assert streak == 2

    def test_current_streak_skips_today_if_no_workout(self, test_db, test_user):
        today = date.today()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)

        _create_workout(test_db, test_user.id, name="Yesterday", workout_date=yesterday)
        _create_workout(test_db, test_user.id, name="Day Before", workout_date=day_before)

        streak = get_current_streak(test_db, test_user.id)
        assert streak == 2

    def test_longest_streak_no_workouts(self, test_db, test_user):
        streak = get_longest_streak(test_db, test_user.id)
        assert streak == 0

    def test_longest_streak_single_workout(self, test_db, test_user):
        _create_workout(test_db, test_user.id, workout_date=date.today())

        streak = get_longest_streak(test_db, test_user.id)
        assert streak == 1

    def test_longest_streak_multiple_streaks(self, test_db, test_user):
        today = date.today()

        for i in range(3):
            _create_workout(
                test_db,
                test_user.id,
                name=f"Recent {i}",
                workout_date=today - timedelta(days=i),
            )

        for i in range(5):
            _create_workout(
                test_db,
                test_user.id,
                name=f"Old {i}",
                workout_date=today - timedelta(days=20 + i),
            )

        streak = get_longest_streak(test_db, test_user.id)
        assert streak == 5

    def test_weekly_average_no_workouts(self, test_db, test_user):
        avg = get_weekly_average(test_db, test_user.id)
        assert avg == 0.0

    def test_weekly_average_with_workouts(self, test_db, test_user):
        today = date.today()
        for i in range(14):
            _create_workout(
                test_db,
                test_user.id,
                name=f"Workout {i}",
                workout_date=today - timedelta(days=i),
            )

        avg = get_weekly_average(test_db, test_user.id)
        assert avg > 0.0

    def test_workouts_this_month(self, test_db, test_user):
        today = date.today()
        first_of_month = date(today.year, today.month, 1)

        _create_workout(test_db, test_user.id, name="This Month 1", workout_date=first_of_month)
        _create_workout(test_db, test_user.id, name="This Month 2", workout_date=today)

        count = get_workouts_this_month(test_db, test_user.id)
        assert count >= 2

    def test_total_workout_count(self, test_db, test_user):
        _create_workout(test_db, test_user.id, name="W1", workout_date=date.today())
        _create_workout(test_db, test_user.id, name="W2", workout_date=date.today() - timedelta(days=30))
        _create_workout(test_db, test_user.id, name="W3", workout_date=date.today() - timedelta(days=60))

        total = get_total_workout_count(test_db, test_user.id)
        assert total == 3


class TestMuscleGroupDistribution:
    """Tests for muscle group distribution analytics."""

    def test_distribution_empty_for_new_user(self, test_db, test_user):
        progress_service = ProgressService(test_db)
        distribution = progress_service.get_muscle_group_distribution(test_user.id)
        assert len(distribution) == 0

    def test_distribution_single_muscle_group(self, test_db, test_user):
        exercise = _create_exercise(test_db, name="Bench Press", muscle_group="chest")
        workout = _create_workout(test_db, test_user.id)
        we = _create_workout_exercise(test_db, workout.id, exercise.id)
        _create_set(test_db, we.id, set_number=1, weight=80, reps=8)
        _create_set(test_db, we.id, set_number=2, weight=80, reps=8)
        _create_set(test_db, we.id, set_number=3, weight=80, reps=8)

        progress_service = ProgressService(test_db)
        distribution = progress_service.get_muscle_group_distribution(test_user.id)

        assert len(distribution) == 1
        assert distribution[0]["muscle_group"] == "chest"
        assert distribution[0]["count"] == 3
        assert distribution[0]["percentage"] == 100.0

    def test_distribution_multiple_muscle_groups(self, test_db, test_user):
        exercise_chest = _create_exercise(test_db, name="Bench Press", muscle_group="chest")
        exercise_back = _create_exercise(test_db, name="Deadlift", muscle_group="back")
        exercise_legs = _create_exercise(test_db, name="Squat", muscle_group="legs")

        workout = _create_workout(test_db, test_user.id)

        we1 = _create_workout_exercise(test_db, workout.id, exercise_chest.id, sort_order=1)
        _create_set(test_db, we1.id, set_number=1, weight=80, reps=8)
        _create_set(test_db, we1.id, set_number=2, weight=80, reps=8)

        we2 = _create_workout_exercise(test_db, workout.id, exercise_back.id, sort_order=2)
        _create_set(test_db, we2.id, set_number=1, weight=100, reps=5)
        _create_set(test_db, we2.id, set_number=2, weight=100, reps=5)
        _create_set(test_db, we2.id, set_number=3, weight=100, reps=5)

        we3 = _create_workout_exercise(test_db, workout.id, exercise_legs.id, sort_order=3)
        _create_set(test_db, we3.id, set_number=1, weight=120, reps=5)

        progress_service = ProgressService(test_db)
        distribution = progress_service.get_muscle_group_distribution(test_user.id)

        assert len(distribution) == 3

        total_sets = sum(d["count"] for d in distribution)
        assert total_sets == 6

        total_pct = sum(d["percentage"] for d in distribution)
        assert abs(total_pct - 100.0) < 0.5

        muscle_groups = {d["muscle_group"] for d in distribution}
        assert "chest" in muscle_groups
        assert "back" in muscle_groups
        assert "legs" in muscle_groups

        back_entry = next(d for d in distribution if d["muscle_group"] == "back")
        assert back_entry["count"] == 3

    def test_distribution_ordered_by_set_count_desc(self, test_db, test_user):
        exercise_chest = _create_exercise(test_db, name="Bench Press", muscle_group="chest")
        exercise_back = _create_exercise(test_db, name="Deadlift", muscle_group="back")

        workout = _create_workout(test_db, test_user.id)

        we1 = _create_workout_exercise(test_db, workout.id, exercise_chest.id, sort_order=1)
        _create_set(test_db, we1.id, set_number=1, weight=80, reps=8)

        we2 = _create_workout_exercise(test_db, workout.id, exercise_back.id, sort_order=2)
        _create_set(test_db, we2.id, set_number=1, weight=100, reps=5)
        _create_set(test_db, we2.id, set_number=2, weight=100, reps=5)
        _create_set(test_db, we2.id, set_number=3, weight=100, reps=5)

        progress_service = ProgressService(test_db)
        distribution = progress_service.get_muscle_group_distribution(test_user.id)

        assert distribution[0]["muscle_group"] == "back"
        assert distribution[0]["count"] == 3
        assert distribution[1]["muscle_group"] == "chest"
        assert distribution[1]["count"] == 1

    def test_distribution_across_multiple_workouts(self, test_db, test_user):
        exercise = _create_exercise(test_db, name="Bench Press", muscle_group="chest")

        workout1 = _create_workout(test_db, test_user.id, name="W1", workout_date=date.today())
        we1 = _create_workout_exercise(test_db, workout1.id, exercise.id)
        _create_set(test_db, we1.id, set_number=1, weight=80, reps=8)
        _create_set(test_db, we1.id, set_number=2, weight=80, reps=8)

        workout2 = _create_workout(test_db, test_user.id, name="W2", workout_date=date.today() - timedelta(days=2))
        we2 = _create_workout_exercise(test_db, workout2.id, exercise.id)
        _create_set(test_db, we2.id, set_number=1, weight=85, reps=6)

        progress_service = ProgressService(test_db)
        distribution = progress_service.get_muscle_group_distribution(test_user.id)

        assert len(distribution) == 1
        assert distribution[0]["muscle_group"] == "chest"
        assert distribution[0]["count"] == 3


class TestProgressServiceSummary:
    """Tests for the ProgressService.get_progress_summary method."""

    def test_progress_summary_returns_all_sections(self, test_db, test_user):
        progress_service = ProgressService(test_db)
        summary = progress_service.get_progress_summary(test_user.id)

        assert "consistency" in summary
        assert "muscle_group_distribution" in summary
        assert "recent_prs" in summary
        assert "all_prs" in summary

    def test_progress_summary_consistency_keys(self, test_db, test_user):
        progress_service = ProgressService(test_db)
        summary = progress_service.get_progress_summary(test_user.id)

        consistency = summary["consistency"]
        assert "current_streak" in consistency
        assert "longest_streak" in consistency
        assert "weekly_average" in consistency
        assert "total_this_month" in consistency
        assert "total_workouts" in consistency

    def test_progress_summary_with_data(self, test_db, test_user):
        from datetime import datetime
        exercise = _create_exercise(test_db)

        workout = _create_workout(test_db, test_user.id, workout_date=date.today())
        we = _create_workout_exercise(test_db, workout.id, exercise.id)
        _create_set(test_db, we.id, set_number=1, weight=100, reps=5)

        _create_personal_record(
            test_db, test_user.id, exercise.id, "weight", 100.0,
            achieved_at=datetime.utcnow(),
        )

        progress_service = ProgressService(test_db)
        summary = progress_service.get_progress_summary(test_user.id)

        assert summary["consistency"]["total_workouts"] >= 1
        assert len(summary["muscle_group_distribution"]) >= 1
        assert len(summary["all_prs"]) >= 1


class TestPRDetectionForWorkout:
    """Tests for detecting PRs across all exercises in a workout."""

    def test_detect_prs_for_workout(self, test_db, test_user):
        exercise = _create_exercise(test_db)
        workout = _create_workout(test_db, test_user.id)
        we = _create_workout_exercise(test_db, workout.id, exercise.id)
        s1 = _create_set(test_db, we.id, set_number=1, weight=100, reps=5)
        s2 = _create_set(test_db, we.id, set_number=2, weight=80, reps=10)

        pr_service = PRService(test_db)
        new_prs = pr_service.detect_prs_for_workout(test_user.id, workout.id)
        test_db.commit()

        assert len(new_prs) > 0

        pr_types = {pr.record_type for pr in new_prs}
        assert "weight" in pr_types

    def test_detect_prs_for_workout_marks_sets(self, test_db, test_user):
        exercise = _create_exercise(test_db)
        workout = _create_workout(test_db, test_user.id)
        we = _create_workout_exercise(test_db, workout.id, exercise.id)
        s1 = _create_set(test_db, we.id, set_number=1, weight=100, reps=5)

        pr_service = PRService(test_db)
        pr_service.detect_prs_for_workout(test_user.id, workout.id)
        test_db.commit()

        test_db.refresh(s1)
        assert s1.is_pr is True

    def test_detect_prs_for_nonexistent_workout(self, test_db, test_user):
        pr_service = PRService(test_db)
        result = pr_service.detect_prs_for_workout(test_user.id, 99999)
        assert result == []

    def test_detect_prs_for_workout_multiple_exercises(self, test_db, test_user):
        exercise1 = _create_exercise(test_db, name="Bench Press", muscle_group="chest")
        exercise2 = _create_exercise(test_db, name="Squat", muscle_group="legs")

        workout = _create_workout(test_db, test_user.id)
        we1 = _create_workout_exercise(test_db, workout.id, exercise1.id, sort_order=1)
        _create_set(test_db, we1.id, set_number=1, weight=100, reps=5)

        we2 = _create_workout_exercise(test_db, workout.id, exercise2.id, sort_order=2)
        _create_set(test_db, we2.id, set_number=1, weight=140, reps=5)

        pr_service = PRService(test_db)
        new_prs = pr_service.detect_prs_for_workout(test_user.id, workout.id)
        test_db.commit()

        exercise_ids_with_prs = {pr.exercise_id for pr in new_prs}
        assert exercise1.id in exercise_ids_with_prs
        assert exercise2.id in exercise_ids_with_prs