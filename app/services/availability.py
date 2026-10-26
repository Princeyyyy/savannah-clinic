from datetime import datetime, date, time, timedelta, timezone
from typing import List
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.exceptions import ResourceNotFoundException, InvalidBookingException
from app.models import Doctor, WorkingHours, Appointment, AppointmentStatus


def validate_slot_alignment(dt: datetime, slot_minutes: int = 30) -> None:
    """Validates that a datetime aligns exactly with slot boundaries (e.g. :00 or :30) and zero seconds."""
    if dt.second != 0 or dt.microsecond != 0 or (dt.minute % slot_minutes != 0):
        raise InvalidBookingException(
            f"Appointment start time must align with {slot_minutes}-minute boundaries (e.g., :00 or :30)."
        )


def get_doctor_available_slots(
    db: Session,
    doctor_id: int,
    query_date: date,
    current_time: datetime | None = None
) -> List[datetime]:
    """
    Computes all open 30-minute slots for a given doctor on a given date.
    Excludes:
    - Breaks defined in doctor's working hours
    - Existing active (BOOKED) appointments
    - Past times
    - Times within the advance booking cutoff (Bonus: 1 hour)
    """
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id, Doctor.is_active.is_(True)).first()
    if not doctor:
        raise ResourceNotFoundException("Doctor", doctor_id)

    # 0 = Monday, 6 = Sunday
    day_of_week = query_date.weekday()
    working_hours = db.query(WorkingHours).filter(
        WorkingHours.doctor_id == doctor_id,
        WorkingHours.day_of_week == day_of_week
    ).first()

    if not working_hours:
        # Doctor does not work on this day
        return []

    if current_time is None:
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
    elif current_time.tzinfo is not None:
        current_time = current_time.astimezone(timezone.utc).replace(tzinfo=None)

    advance_cutoff = current_time + timedelta(hours=settings.MIN_ADVANCE_BOOKING_HOURS)

    # Query all active bookings for this doctor on query_date
    start_of_day = datetime.combine(query_date, time.min)
    end_of_day = datetime.combine(query_date, time.max)

    booked_appointments = db.query(Appointment.start_time).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.status == AppointmentStatus.BOOKED.value,
        Appointment.start_time >= start_of_day,
        Appointment.start_time <= end_of_day
    ).all()
    booked_starts = {appt[0] for appt in booked_appointments}

    available_slots: List[datetime] = []
    slot_duration = timedelta(minutes=settings.SLOT_DURATION_MINUTES)

    slot_time = datetime.combine(query_date, working_hours.start_time)
    work_end_dt = datetime.combine(query_date, working_hours.end_time)

    break_start_dt = (
        datetime.combine(query_date, working_hours.break_start)
        if working_hours.break_start
        else None
    )
    break_end_dt = (
        datetime.combine(query_date, working_hours.break_end)
        if working_hours.break_end
        else None
    )

    while slot_time + slot_duration <= work_end_dt:
        slot_end = slot_time + slot_duration

        # Check if slot overlaps with doctor's break
        in_break = False
        if break_start_dt and break_end_dt:
            if not (slot_end <= break_start_dt or slot_time >= break_end_dt):
                in_break = True

        if not in_break:
            # Check if slot is not in the past and satisfies advance booking cutoff
            if slot_time >= advance_cutoff:
                # Check if slot is not already booked
                if slot_time not in booked_starts:
                    available_slots.append(slot_time)

        slot_time += slot_duration

    return available_slots
