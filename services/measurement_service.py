from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.orm import Session

from models.body_measurement import BodyMeasurement


class MeasurementService:

    def __init__(self, db: Session):
        self.db = db

    def create_measurement(
        self,
        user_id: int,
        measurement_date: date,
        weight: Optional[float] = None,
        body_fat_pct: Optional[float] = None,
        chest: Optional[float] = None,
        waist: Optional[float] = None,
        hips: Optional[float] = None,
        biceps: Optional[float] = None,
        thighs: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> BodyMeasurement:
        existing = self.db.execute(
            select(BodyMeasurement).where(
                and_(
                    BodyMeasurement.user_id == user_id,
                    BodyMeasurement.measurement_date == measurement_date,
                )
            )
        ).scalar_one_or_none()

        if existing is not None:
            raise ValueError(
                f"A measurement for {measurement_date} already exists. "
                "Please edit the existing entry instead."
            )

        measurement = BodyMeasurement(
            user_id=user_id,
            measurement_date=measurement_date,
            weight=weight,
            body_fat_pct=body_fat_pct,
            chest=chest,
            waist=waist,
            hips=hips,
            left_arm=biceps,
            right_arm=biceps,
            left_thigh=thighs,
            right_thigh=thighs,
        )

        self.db.add(measurement)
        self.db.commit()
        self.db.refresh(measurement)
        return measurement

    def update_measurement(
        self,
        user_id: int,
        measurement_id: int,
        measurement_date: Optional[date] = None,
        weight: Optional[float] = ...,
        body_fat_pct: Optional[float] = ...,
        chest: Optional[float] = ...,
        waist: Optional[float] = ...,
        hips: Optional[float] = ...,
        biceps: Optional[float] = ...,
        thighs: Optional[float] = ...,
        notes: Optional[str] = ...,
    ) -> BodyMeasurement:
        measurement = self.db.execute(
            select(BodyMeasurement).where(
                and_(
                    BodyMeasurement.id == measurement_id,
                    BodyMeasurement.user_id == user_id,
                )
            )
        ).scalar_one_or_none()

        if measurement is None:
            raise LookupError("Measurement not found.")

        if measurement_date is not None and measurement_date != measurement.measurement_date:
            conflict = self.db.execute(
                select(BodyMeasurement).where(
                    and_(
                        BodyMeasurement.user_id == user_id,
                        BodyMeasurement.measurement_date == measurement_date,
                        BodyMeasurement.id != measurement_id,
                    )
                )
            ).scalar_one_or_none()
            if conflict is not None:
                raise ValueError(
                    f"A measurement for {measurement_date} already exists."
                )
            measurement.measurement_date = measurement_date

        sentinel = ...

        if weight is not sentinel:
            measurement.weight = weight
        if body_fat_pct is not sentinel:
            measurement.body_fat_pct = body_fat_pct
        if chest is not sentinel:
            measurement.chest = chest
        if waist is not sentinel:
            measurement.waist = waist
        if hips is not sentinel:
            measurement.hips = hips
        if biceps is not sentinel:
            measurement.left_arm = biceps
            measurement.right_arm = biceps
        if thighs is not sentinel:
            measurement.left_thigh = thighs
            measurement.right_thigh = thighs

        self.db.commit()
        self.db.refresh(measurement)
        return measurement

    def delete_measurement(self, user_id: int, measurement_id: int) -> None:
        measurement = self.db.execute(
            select(BodyMeasurement).where(
                and_(
                    BodyMeasurement.id == measurement_id,
                    BodyMeasurement.user_id == user_id,
                )
            )
        ).scalar_one_or_none()

        if measurement is None:
            raise LookupError("Measurement not found.")

        self.db.delete(measurement)
        self.db.commit()

    def get_measurement(self, user_id: int, measurement_id: int) -> Optional[BodyMeasurement]:
        return self.db.execute(
            select(BodyMeasurement).where(
                and_(
                    BodyMeasurement.id == measurement_id,
                    BodyMeasurement.user_id == user_id,
                )
            )
        ).scalar_one_or_none()

    def list_measurements(
        self,
        user_id: int,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 20
        if per_page > 100:
            per_page = 100

        total_result = self.db.execute(
            select(func.count(BodyMeasurement.id)).where(
                BodyMeasurement.user_id == user_id
            )
        )
        total = total_result.scalar() or 0

        total_pages = max(1, (total + per_page - 1) // per_page)

        if page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page

        rows = self.db.execute(
            select(BodyMeasurement)
            .where(BodyMeasurement.user_id == user_id)
            .order_by(BodyMeasurement.measurement_date.desc())
            .offset(offset)
            .limit(per_page)
        ).scalars().all()

        measurements = []
        for m in rows:
            measurements.append(_measurement_to_dict(m))

        return {
            "measurements": measurements,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    def get_existing_dates(self, user_id: int) -> list[str]:
        rows = self.db.execute(
            select(BodyMeasurement.measurement_date)
            .where(BodyMeasurement.user_id == user_id)
            .order_by(BodyMeasurement.measurement_date.desc())
        ).scalars().all()
        return [d.isoformat() if isinstance(d, date) else str(d) for d in rows]

    def get_trend_summary(self, user_id: int) -> list[dict]:
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)

        latest = self.db.execute(
            select(BodyMeasurement)
            .where(BodyMeasurement.user_id == user_id)
            .order_by(BodyMeasurement.measurement_date.desc())
            .limit(1)
        ).scalar_one_or_none()

        previous = self.db.execute(
            select(BodyMeasurement)
            .where(
                and_(
                    BodyMeasurement.user_id == user_id,
                    BodyMeasurement.measurement_date <= thirty_days_ago,
                )
            )
            .order_by(BodyMeasurement.measurement_date.desc())
            .limit(1)
        ).scalar_one_or_none()

        trends = []

        # Current Weight
        current_weight = latest.weight if latest else None
        trends.append(
            _build_trend(
                metric="Current Weight",
                current_value=current_weight,
                previous_value=None,
            )
        )

        # Weight Change 30d
        prev_weight = previous.weight if previous else None
        weight_delta = None
        weight_delta_pct = None
        weight_direction = None
        if current_weight is not None and prev_weight is not None:
            weight_delta = round(current_weight - prev_weight, 1)
            if prev_weight != 0:
                weight_delta_pct = round((weight_delta / prev_weight) * 100, 1)
            if weight_delta > 0:
                weight_direction = "up"
            elif weight_delta < 0:
                weight_direction = "down"
            else:
                weight_direction = "stable"
        trends.append({
            "metric": "Weight Change 30d",
            "current_value": weight_delta,
            "previous_value": prev_weight,
            "delta": weight_delta,
            "delta_pct": weight_delta_pct,
            "trend_direction": weight_direction,
        })

        # Current Body Fat
        current_bf = latest.body_fat_pct if latest else None
        trends.append(
            _build_trend(
                metric="Current Body Fat",
                current_value=current_bf,
                previous_value=None,
            )
        )

        # Body Fat Change 30d
        prev_bf = previous.body_fat_pct if previous else None
        bf_delta = None
        bf_delta_pct = None
        bf_direction = None
        if current_bf is not None and prev_bf is not None:
            bf_delta = round(current_bf - prev_bf, 1)
            if prev_bf != 0:
                bf_delta_pct = round((bf_delta / prev_bf) * 100, 1)
            if bf_delta > 0:
                bf_direction = "up"
            elif bf_delta < 0:
                bf_direction = "down"
            else:
                bf_direction = "stable"
        trends.append({
            "metric": "Body Fat Change 30d",
            "current_value": bf_delta,
            "previous_value": prev_bf,
            "delta": bf_delta,
            "delta_pct": bf_delta_pct,
            "trend_direction": bf_direction,
        })

        return trends

    def get_latest_weight(self, user_id: int) -> Optional[float]:
        latest = self.db.execute(
            select(BodyMeasurement.weight)
            .where(
                and_(
                    BodyMeasurement.user_id == user_id,
                    BodyMeasurement.weight.isnot(None),
                )
            )
            .order_by(BodyMeasurement.measurement_date.desc())
            .limit(1)
        ).scalar_one_or_none()
        return latest


def _measurement_to_dict(m: BodyMeasurement) -> dict:
    return {
        "id": m.id,
        "user_id": m.user_id,
        "measurement_date": m.measurement_date,
        "weight": m.weight,
        "body_fat_pct": m.body_fat_pct,
        "chest": m.chest,
        "waist": m.waist,
        "hips": m.hips,
        "biceps": m.left_arm,
        "thighs": m.left_thigh,
        "notes": None,
        "created_at": m.created_at,
        "updated_at": None,
    }


def _build_trend(
    metric: str,
    current_value: Optional[float],
    previous_value: Optional[float],
) -> dict:
    delta = None
    delta_pct = None
    trend_direction = None

    if current_value is not None and previous_value is not None:
        delta = round(current_value - previous_value, 1)
        if previous_value != 0:
            delta_pct = round((delta / previous_value) * 100, 1)
        if delta > 0:
            trend_direction = "up"
        elif delta < 0:
            trend_direction = "down"
        else:
            trend_direction = "stable"

    return {
        "metric": metric,
        "current_value": current_value,
        "previous_value": previous_value,
        "delta": delta,
        "delta_pct": delta_pct,
        "trend_direction": trend_direction,
    }