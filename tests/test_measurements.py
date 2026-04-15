import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from tests.conftest import *
from models.body_measurement import BodyMeasurement
from services.measurement_service import MeasurementService


class TestMeasurementCreation:
    """Tests for creating body measurements."""

    def test_create_measurement_success(self, authenticated_client, test_user, test_db):
        """Test that an authenticated user can create a new measurement."""
        response = authenticated_client.post(
            "/measurements/new",
            data={
                "measurement_date": date.today().isoformat(),
                "weight": "80.5",
                "body_fat_pct": "15.0",
                "chest": "100.0",
                "waist": "80.0",
                "hips": "95.0",
                "biceps": "35.0",
                "thighs": "55.0",
                "notes": "Morning measurement",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/measurements" in response.headers["location"]

        measurement = (
            test_db.query(BodyMeasurement)
            .filter(BodyMeasurement.user_id == test_user.id)
            .first()
        )
        assert measurement is not None
        assert measurement.weight == 80.5
        assert measurement.body_fat_pct == 15.0
        assert measurement.chest == 100.0
        assert measurement.waist == 80.0
        assert measurement.hips == 95.0
        assert measurement.left_arm == 35.0
        assert measurement.left_thigh == 55.0

    def test_create_measurement_weight_only(self, authenticated_client, test_user, test_db):
        """Test creating a measurement with only weight filled in."""
        response = authenticated_client.post(
            "/measurements/new",
            data={
                "measurement_date": date.today().isoformat(),
                "weight": "75.0",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        measurement = (
            test_db.query(BodyMeasurement)
            .filter(BodyMeasurement.user_id == test_user.id)
            .first()
        )
        assert measurement is not None
        assert measurement.weight == 75.0
        assert measurement.body_fat_pct is None
        assert measurement.chest is None
        assert measurement.waist is None

    def test_create_measurement_invalid_date(self, authenticated_client):
        """Test creating a measurement with an invalid date format."""
        response = authenticated_client.post(
            "/measurements/new",
            data={
                "measurement_date": "not-a-date",
                "weight": "80.0",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/measurements/new" in response.headers["location"]

    def test_create_measurement_unauthenticated(self, test_client):
        """Test that unauthenticated users cannot create measurements."""
        response = test_client.post(
            "/measurements/new",
            data={
                "measurement_date": date.today().isoformat(),
                "weight": "80.0",
            },
            follow_redirects=False,
        )
        assert response.status_code in (401, 302, 303)


class TestMeasurementUniqueConstraint:
    """Tests for the unique constraint on user_id + measurement_date."""

    def test_duplicate_date_rejected(self, authenticated_client, test_user, test_db):
        """Test that creating two measurements on the same date for the same user is rejected."""
        target_date = date.today().isoformat()

        response1 = authenticated_client.post(
            "/measurements/new",
            data={
                "measurement_date": target_date,
                "weight": "80.0",
            },
            follow_redirects=False,
        )
        assert response1.status_code == 303
        assert "/measurements" in response1.headers["location"]
        assert "/measurements/new" not in response1.headers["location"]

        response2 = authenticated_client.post(
            "/measurements/new",
            data={
                "measurement_date": target_date,
                "weight": "81.0",
            },
            follow_redirects=False,
        )
        assert response2.status_code == 303
        assert "/measurements/new" in response2.headers["location"]

        count = (
            test_db.query(BodyMeasurement)
            .filter(
                BodyMeasurement.user_id == test_user.id,
            )
            .count()
        )
        assert count == 1

    def test_different_dates_allowed(self, authenticated_client, test_user, test_db):
        """Test that measurements on different dates are allowed."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        response1 = authenticated_client.post(
            "/measurements/new",
            data={
                "measurement_date": today.isoformat(),
                "weight": "80.0",
            },
            follow_redirects=False,
        )
        assert response1.status_code == 303

        response2 = authenticated_client.post(
            "/measurements/new",
            data={
                "measurement_date": yesterday.isoformat(),
                "weight": "79.5",
            },
            follow_redirects=False,
        )
        assert response2.status_code == 303

        count = (
            test_db.query(BodyMeasurement)
            .filter(BodyMeasurement.user_id == test_user.id)
            .count()
        )
        assert count == 2

    def test_different_users_same_date_allowed(self, test_db, test_user, admin_user):
        """Test that different users can have measurements on the same date."""
        service = MeasurementService(test_db)
        target_date = date.today()

        m1 = service.create_measurement(
            user_id=test_user.id,
            measurement_date=target_date,
            weight=80.0,
        )
        assert m1 is not None

        m2 = service.create_measurement(
            user_id=admin_user.id,
            measurement_date=target_date,
            weight=90.0,
        )
        assert m2 is not None
        assert m1.id != m2.id


class TestMeasurementEdit:
    """Tests for editing body measurements."""

    def test_edit_measurement_success(self, authenticated_client, test_user, test_db):
        """Test that a user can edit their own measurement."""
        service = MeasurementService(test_db)
        measurement = service.create_measurement(
            user_id=test_user.id,
            measurement_date=date.today(),
            weight=80.0,
            chest=100.0,
        )

        response = authenticated_client.post(
            f"/measurements/{measurement.id}/edit",
            data={
                "measurement_date": date.today().isoformat(),
                "weight": "82.0",
                "chest": "101.0",
                "waist": "79.0",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/measurements" in response.headers["location"]

        test_db.refresh(measurement)
        assert measurement.weight == 82.0
        assert measurement.chest == 101.0
        assert measurement.waist == 79.0

    def test_edit_measurement_change_date(self, authenticated_client, test_user, test_db):
        """Test that a user can change the date of a measurement."""
        service = MeasurementService(test_db)
        original_date = date.today() - timedelta(days=5)
        new_date = date.today() - timedelta(days=3)

        measurement = service.create_measurement(
            user_id=test_user.id,
            measurement_date=original_date,
            weight=80.0,
        )

        response = authenticated_client.post(
            f"/measurements/{measurement.id}/edit",
            data={
                "measurement_date": new_date.isoformat(),
                "weight": "80.0",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        test_db.refresh(measurement)
        assert measurement.measurement_date == new_date

    def test_edit_measurement_date_conflict(self, authenticated_client, test_user, test_db):
        """Test that editing a measurement to a date that already has a measurement fails."""
        service = MeasurementService(test_db)
        date1 = date.today() - timedelta(days=2)
        date2 = date.today() - timedelta(days=1)

        service.create_measurement(
            user_id=test_user.id,
            measurement_date=date1,
            weight=80.0,
        )
        m2 = service.create_measurement(
            user_id=test_user.id,
            measurement_date=date2,
            weight=81.0,
        )

        response = authenticated_client.post(
            f"/measurements/{m2.id}/edit",
            data={
                "measurement_date": date1.isoformat(),
                "weight": "81.0",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        test_db.refresh(m2)
        assert m2.measurement_date == date2

    def test_edit_nonexistent_measurement(self, authenticated_client):
        """Test editing a measurement that doesn't exist."""
        response = authenticated_client.post(
            "/measurements/99999/edit",
            data={
                "measurement_date": date.today().isoformat(),
                "weight": "80.0",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/measurements" in response.headers["location"]

    def test_edit_measurement_form_page(self, authenticated_client, test_user, test_db):
        """Test that the edit form page loads correctly."""
        service = MeasurementService(test_db)
        measurement = service.create_measurement(
            user_id=test_user.id,
            measurement_date=date.today(),
            weight=80.0,
        )

        response = authenticated_client.get(
            f"/measurements/{measurement.id}/edit",
            follow_redirects=False,
        )
        assert response.status_code == 200


class TestMeasurementDelete:
    """Tests for deleting body measurements."""

    def test_delete_measurement_success(self, authenticated_client, test_user, test_db):
        """Test that a user can delete their own measurement."""
        service = MeasurementService(test_db)
        measurement = service.create_measurement(
            user_id=test_user.id,
            measurement_date=date.today(),
            weight=80.0,
        )
        measurement_id = measurement.id

        response = authenticated_client.post(
            f"/measurements/{measurement_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/measurements" in response.headers["location"]

        deleted = (
            test_db.query(BodyMeasurement)
            .filter(BodyMeasurement.id == measurement_id)
            .first()
        )
        assert deleted is None

    def test_delete_nonexistent_measurement(self, authenticated_client):
        """Test deleting a measurement that doesn't exist."""
        response = authenticated_client.post(
            "/measurements/99999/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/measurements" in response.headers["location"]

    def test_delete_measurement_unauthenticated(self, test_client, test_user, test_db):
        """Test that unauthenticated users cannot delete measurements."""
        service = MeasurementService(test_db)
        measurement = service.create_measurement(
            user_id=test_user.id,
            measurement_date=date.today(),
            weight=80.0,
        )

        response = test_client.post(
            f"/measurements/{measurement.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code in (401, 302, 303)

        still_exists = (
            test_db.query(BodyMeasurement)
            .filter(BodyMeasurement.id == measurement.id)
            .first()
        )
        assert still_exists is not None


class TestMeasurementOwnership:
    """Tests for ownership enforcement on measurements."""

    def test_cannot_view_other_users_measurement(
        self, authenticated_client, admin_user, test_db
    ):
        """Test that a user cannot view another user's measurement edit form."""
        service = MeasurementService(test_db)
        measurement = service.create_measurement(
            user_id=admin_user.id,
            measurement_date=date.today(),
            weight=90.0,
        )

        response = authenticated_client.get(
            f"/measurements/{measurement.id}/edit",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/measurements" in response.headers["location"]

    def test_cannot_edit_other_users_measurement(
        self, authenticated_client, admin_user, test_db
    ):
        """Test that a user cannot edit another user's measurement."""
        service = MeasurementService(test_db)
        measurement = service.create_measurement(
            user_id=admin_user.id,
            measurement_date=date.today(),
            weight=90.0,
        )

        response = authenticated_client.post(
            f"/measurements/{measurement.id}/edit",
            data={
                "measurement_date": date.today().isoformat(),
                "weight": "100.0",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        test_db.refresh(measurement)
        assert measurement.weight == 90.0

    def test_cannot_delete_other_users_measurement(
        self, authenticated_client, admin_user, test_db
    ):
        """Test that a user cannot delete another user's measurement."""
        service = MeasurementService(test_db)
        measurement = service.create_measurement(
            user_id=admin_user.id,
            measurement_date=date.today(),
            weight=90.0,
        )
        measurement_id = measurement.id

        response = authenticated_client.post(
            f"/measurements/{measurement_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303

        still_exists = (
            test_db.query(BodyMeasurement)
            .filter(BodyMeasurement.id == measurement_id)
            .first()
        )
        assert still_exists is not None


class TestMeasurementTrendSummary:
    """Tests for trend summary calculation."""

    def test_trend_summary_with_no_data(self, test_user, test_db):
        """Test trend summary when no measurements exist."""
        service = MeasurementService(test_db)
        trends = service.get_trend_summary(user_id=test_user.id)

        assert isinstance(trends, list)
        assert len(trends) >= 1

        current_weight_trend = trends[0]
        assert current_weight_trend["metric"] == "Current Weight"
        assert current_weight_trend["current_value"] is None

    def test_trend_summary_with_single_measurement(self, test_user, test_db):
        """Test trend summary with only one measurement."""
        service = MeasurementService(test_db)
        service.create_measurement(
            user_id=test_user.id,
            measurement_date=date.today(),
            weight=80.0,
            body_fat_pct=15.0,
        )

        trends = service.get_trend_summary(user_id=test_user.id)
        assert isinstance(trends, list)

        current_weight = next(
            (t for t in trends if t["metric"] == "Current Weight"), None
        )
        assert current_weight is not None
        assert current_weight["current_value"] == 80.0

        current_bf = next(
            (t for t in trends if t["metric"] == "Current Body Fat"), None
        )
        assert current_bf is not None
        assert current_bf["current_value"] == 15.0

    def test_trend_summary_with_weight_change(self, test_user, test_db):
        """Test trend summary calculates weight change over 30 days."""
        service = MeasurementService(test_db)

        old_date = date.today() - timedelta(days=35)
        service.create_measurement(
            user_id=test_user.id,
            measurement_date=old_date,
            weight=85.0,
        )

        service.create_measurement(
            user_id=test_user.id,
            measurement_date=date.today(),
            weight=80.0,
        )

        trends = service.get_trend_summary(user_id=test_user.id)

        weight_change = next(
            (t for t in trends if t["metric"] == "Weight Change 30d"), None
        )
        assert weight_change is not None
        assert weight_change["delta"] is not None
        assert weight_change["delta"] == -5.0
        assert weight_change["trend_direction"] == "down"

    def test_trend_summary_weight_increase(self, test_user, test_db):
        """Test trend summary shows weight increase correctly."""
        service = MeasurementService(test_db)

        old_date = date.today() - timedelta(days=35)
        service.create_measurement(
            user_id=test_user.id,
            measurement_date=old_date,
            weight=75.0,
        )

        service.create_measurement(
            user_id=test_user.id,
            measurement_date=date.today(),
            weight=80.0,
        )

        trends = service.get_trend_summary(user_id=test_user.id)

        weight_change = next(
            (t for t in trends if t["metric"] == "Weight Change 30d"), None
        )
        assert weight_change is not None
        assert weight_change["delta"] == 5.0
        assert weight_change["trend_direction"] == "up"

    def test_trend_summary_no_change(self, test_user, test_db):
        """Test trend summary when weight hasn't changed."""
        service = MeasurementService(test_db)

        old_date = date.today() - timedelta(days=35)
        service.create_measurement(
            user_id=test_user.id,
            measurement_date=old_date,
            weight=80.0,
        )

        service.create_measurement(
            user_id=test_user.id,
            measurement_date=date.today(),
            weight=80.0,
        )

        trends = service.get_trend_summary(user_id=test_user.id)

        weight_change = next(
            (t for t in trends if t["metric"] == "Weight Change 30d"), None
        )
        assert weight_change is not None
        assert weight_change["delta"] == 0.0
        assert weight_change["trend_direction"] == "stable"


class TestMeasurementListPage:
    """Tests for the measurements list page."""

    def test_list_measurements_page_loads(self, authenticated_client):
        """Test that the measurements list page loads for authenticated users."""
        response = authenticated_client.get("/measurements")
        assert response.status_code == 200
        assert b"Body Measurements" in response.content or b"Measurements" in response.content

    def test_list_measurements_unauthenticated(self, test_client):
        """Test that unauthenticated users cannot access the measurements list."""
        response = test_client.get("/measurements", follow_redirects=False)
        assert response.status_code in (401, 302, 303)

    def test_new_measurement_form_loads(self, authenticated_client):
        """Test that the new measurement form page loads."""
        response = authenticated_client.get("/measurements/new")
        assert response.status_code == 200

    def test_list_shows_user_measurements_only(
        self, authenticated_client, test_user, admin_user, test_db
    ):
        """Test that the list page only shows the current user's measurements."""
        service = MeasurementService(test_db)

        service.create_measurement(
            user_id=test_user.id,
            measurement_date=date.today(),
            weight=80.0,
        )

        service.create_measurement(
            user_id=admin_user.id,
            measurement_date=date.today(),
            weight=90.0,
        )

        response = authenticated_client.get("/measurements")
        assert response.status_code == 200
        assert b"80.0" in response.content
        assert b"90.0" not in response.content


class TestMeasurementServiceDirectly:
    """Tests for the MeasurementService directly."""

    def test_get_latest_weight(self, test_user, test_db):
        """Test getting the latest weight for a user."""
        service = MeasurementService(test_db)

        assert service.get_latest_weight(test_user.id) is None

        service.create_measurement(
            user_id=test_user.id,
            measurement_date=date.today() - timedelta(days=5),
            weight=78.0,
        )
        service.create_measurement(
            user_id=test_user.id,
            measurement_date=date.today(),
            weight=80.0,
        )

        latest = service.get_latest_weight(test_user.id)
        assert latest == 80.0

    def test_get_existing_dates(self, test_user, test_db):
        """Test getting existing measurement dates for a user."""
        service = MeasurementService(test_db)

        dates = service.get_existing_dates(test_user.id)
        assert dates == []

        d1 = date.today() - timedelta(days=2)
        d2 = date.today()
        service.create_measurement(
            user_id=test_user.id,
            measurement_date=d1,
            weight=79.0,
        )
        service.create_measurement(
            user_id=test_user.id,
            measurement_date=d2,
            weight=80.0,
        )

        dates = service.get_existing_dates(test_user.id)
        assert len(dates) == 2
        assert d2.isoformat() in dates
        assert d1.isoformat() in dates

    def test_list_measurements_pagination(self, test_user, test_db):
        """Test that measurement listing supports pagination."""
        service = MeasurementService(test_db)

        for i in range(25):
            service.create_measurement(
                user_id=test_user.id,
                measurement_date=date.today() - timedelta(days=i),
                weight=80.0 + i * 0.1,
            )

        result = service.list_measurements(user_id=test_user.id, page=1, per_page=10)
        assert result["total"] == 25
        assert len(result["measurements"]) == 10
        assert result["page"] == 1
        assert result["total_pages"] == 3

        result2 = service.list_measurements(user_id=test_user.id, page=3, per_page=10)
        assert len(result2["measurements"]) == 5
        assert result2["page"] == 3

    def test_create_measurement_duplicate_raises_value_error(self, test_user, test_db):
        """Test that creating a duplicate measurement raises ValueError."""
        service = MeasurementService(test_db)
        target_date = date.today()

        service.create_measurement(
            user_id=test_user.id,
            measurement_date=target_date,
            weight=80.0,
        )

        with pytest.raises(ValueError, match="already exists"):
            service.create_measurement(
                user_id=test_user.id,
                measurement_date=target_date,
                weight=81.0,
            )

    def test_delete_nonexistent_raises_lookup_error(self, test_user, test_db):
        """Test that deleting a nonexistent measurement raises LookupError."""
        service = MeasurementService(test_db)

        with pytest.raises(LookupError, match="not found"):
            service.delete_measurement(user_id=test_user.id, measurement_id=99999)

    def test_get_measurement_returns_none_for_wrong_user(
        self, test_user, admin_user, test_db
    ):
        """Test that get_measurement returns None when user doesn't own the measurement."""
        service = MeasurementService(test_db)
        measurement = service.create_measurement(
            user_id=admin_user.id,
            measurement_date=date.today(),
            weight=90.0,
        )

        result = service.get_measurement(
            user_id=test_user.id, measurement_id=measurement.id
        )
        assert result is None

    def test_update_measurement_not_found_raises_lookup_error(self, test_user, test_db):
        """Test that updating a nonexistent measurement raises LookupError."""
        service = MeasurementService(test_db)

        with pytest.raises(LookupError, match="not found"):
            service.update_measurement(
                user_id=test_user.id,
                measurement_id=99999,
                weight=80.0,
            )