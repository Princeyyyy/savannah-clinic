from datetime import datetime, date, time, timedelta, timezone
from typing import List, Dict, Any, Tuple
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


def format_slot_label(start_dt: datetime, end_dt: datetime) -> str:
    """Formats start and end times into a clean readable string (e.g. '09:00 AM - 09:30 AM')."""
    return f"{start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}"


def get_clinic_now() -> datetime:
    """
    Returns the current datetime in the clinic's operating timezone (e.g. Africa/Nairobi, UTC+3)
    stripped of tzinfo so it can be accurately compared against doctor working hours and naive slot times.
    """
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo(settings.CLINIC_TIMEZONE)
        return datetime.now(tz).replace(tzinfo=None)
    except Exception:
        return datetime.now(timezone.utc).replace(tzinfo=None)


def get_doctor_schedule_slots(
    db: Session,
    doctor_id: int,
    query_date: date,
    current_time: datetime | None = None
) -> Tuple[List[datetime], List[Dict[str, Any]]]:
    """
    Computes all slots for a doctor on a given day, categorizing each slot as:
    - AVAILABLE: Open for booking (green)
    - BOOKED: Already booked by a patient (red)
    - BREAK: Doctor lunch break (amber/grey)
    - CUTOFF: Within the advance booking window (< 1 hour from now)
    - PAST: In the past
    
    Returns a tuple of (available_slots, all_slots_details).
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
        return [], []

    if current_time is None:
        current_time = get_clinic_now()
    elif current_time.tzinfo is not None:
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(settings.CLINIC_TIMEZONE)
            current_time = current_time.astimezone(tz).replace(tzinfo=None)
        except Exception:
            current_time = current_time.astimezone(timezone.utc).replace(tzinfo=None)

    advance_cutoff = current_time + timedelta(hours=settings.MIN_ADVANCE_BOOKING_HOURS)

    # Query all active bookings for this doctor on query_date
    start_of_day = datetime.combine(query_date, time.min)
    end_of_day = datetime.combine(query_date, time.max)

    booked_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.status == AppointmentStatus.BOOKED.value,
        Appointment.start_time >= start_of_day,
        Appointment.start_time <= end_of_day
    ).all()

    # Map start_time to appointment record
    booked_map = {appt.start_time: appt for appt in booked_appointments}

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

    available_slots: List[datetime] = []
    all_slots_details: List[Dict[str, Any]] = []

    while slot_time + slot_duration <= work_end_dt:
        slot_end = slot_time + slot_duration
        label = format_slot_label(slot_time, slot_end)

        # Check if slot overlaps with doctor's break
        in_break = False
        if break_start_dt and break_end_dt:
            if not (slot_end <= break_start_dt or slot_time >= break_end_dt):
                in_break = True

        if in_break:
            slot_status = "BREAK"
            appt_id = None
            pat_name = None
        elif slot_time in booked_map:
            slot_status = "BOOKED"
            active_appt = booked_map[slot_time]
            appt_id = active_appt.id
            pat_name = active_appt.patient.name if active_appt.patient else f"Patient #{active_appt.patient_id}"
        elif slot_time < current_time:
            slot_status = "PAST"
            appt_id = None
            pat_name = None
        elif slot_time < advance_cutoff:
            slot_status = "CUTOFF"
            appt_id = None
            pat_name = None
        else:
            slot_status = "AVAILABLE"
            appt_id = None
            pat_name = None
            available_slots.append(slot_time)

        all_slots_details.append({
            "start_time": slot_time.isoformat(),
            "end_time": slot_end.isoformat(),
            "status": slot_status,
            "label": label,
            "appointment_id": appt_id,
            "patient_name": pat_name,
        })

        slot_time += slot_duration

    return available_slots, all_slots_details


def get_doctor_available_slots(
    db: Session,
    doctor_id: int,
    query_date: date,
    current_time: datetime | None = None
) -> List[datetime]:
    """Preserves original function signature for existing callers and tests."""
    available_slots, _ = get_doctor_schedule_slots(
        db=db,
        doctor_id=doctor_id,
        query_date=query_date,
        current_time=current_time
    )
    return available_slots
