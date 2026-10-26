from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.core.exceptions import (
    ResourceNotFoundException,
    InvalidBookingException,
    SlotConflictException,
    AppointmentAlreadyCancelledException,
)
from app.models import Doctor, WorkingHours, Patient, Appointment, AppointmentStatus
from app.services.availability import validate_slot_alignment, get_clinic_now


def validate_booking_time(
    db: Session,
    doctor_id: int,
    start_time: datetime,
    current_time: datetime | None = None,
    exclude_appointment_id: int | None = None
) -> datetime:
    """
    Validates that a requested slot start_time:
    1. Aligns with 30-minute boundaries.
    2. Is not in the past.
    3. Respects the advance booking cutoff (1 hour).
    4. Falls within the doctor's working hours and outside lunch breaks.
    5. Is not already taken by another active booking.
    Returns normalized naive datetime in clinic time.
    """
    # Normalize start_time to naive clinic time if timezone is present
    if start_time.tzinfo is not None:
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(settings.CLINIC_TIMEZONE)
            start_time = start_time.astimezone(tz).replace(tzinfo=None)
        except Exception:
            start_time = start_time.astimezone(timezone.utc).replace(tzinfo=None)

    validate_slot_alignment(start_time, settings.SLOT_DURATION_MINUTES)

    if current_time is None:
        current_time = get_clinic_now()
    elif current_time.tzinfo is not None:
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(settings.CLINIC_TIMEZONE)
            current_time = current_time.astimezone(tz).replace(tzinfo=None)
        except Exception:
            current_time = current_time.astimezone(timezone.utc).replace(tzinfo=None)

    # Validate not in the past
    if start_time < current_time:
        raise InvalidBookingException("Cannot book an appointment slot in the past.")

    # Check doctor working hours
    slot_date = start_time.date()
    slot_time = start_time.time()
    slot_end_time = (start_time + timedelta(minutes=settings.SLOT_DURATION_MINUTES)).time()

    day_of_week = slot_date.weekday()
    working_hours = db.query(WorkingHours).filter(
        WorkingHours.doctor_id == doctor_id,
        WorkingHours.day_of_week == day_of_week
    ).first()

    if not working_hours:
        raise InvalidBookingException("Doctor does not work on this day.")

    if slot_time < working_hours.start_time or slot_end_time > working_hours.end_time:
        raise InvalidBookingException(
            f"Requested time is outside doctor's working hours ({working_hours.start_time.strftime('%H:%M')} - {working_hours.end_time.strftime('%H:%M')})."
        )

    # Check lunch break
    if working_hours.break_start and working_hours.break_end:
        if not (slot_end_time <= working_hours.break_start or slot_time >= working_hours.break_end):
            raise InvalidBookingException(
                f"Requested time falls during doctor's break ({working_hours.break_start.strftime('%H:%M')} - {working_hours.break_end.strftime('%H:%M')})."
            )

    # Check existing active booking
    conflict_query = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.start_time == start_time,
        Appointment.status == AppointmentStatus.BOOKED.value
    )
    if exclude_appointment_id:
        conflict_query = conflict_query.filter(Appointment.id != exclude_appointment_id)

    if conflict_query.first():
        raise SlotConflictException("The requested appointment slot is already taken.")

    return start_time


def book_appointment(
    db: Session,
    doctor_id: int,
    patient_id: int,
    start_time: datetime,
    current_time: datetime | None = None
) -> Appointment:
    """Books an appointment, validating constraints and protecting against double-booking race conditions."""
    # Verify doctor exists
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id, Doctor.is_active.is_(True)).first()
    if not doctor:
        raise ResourceNotFoundException("Doctor", doctor_id)

    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise ResourceNotFoundException("Patient", patient_id)

    normalized_start = validate_booking_time(db, doctor_id, start_time, current_time)
    end_time = normalized_start + timedelta(minutes=settings.SLOT_DURATION_MINUTES)

    appointment = Appointment(
        doctor_id=doctor_id,
        patient_id=patient_id,
        start_time=normalized_start,
        end_time=end_time,
        status=AppointmentStatus.BOOKED.value
    )

    try:
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
    except IntegrityError:
        db.rollback()
        raise SlotConflictException("The requested appointment slot is already taken.")

    return appointment


def cancel_appointment(
    db: Session,
    appointment_id: int,
    reason: str
) -> Appointment:
    """Cancels an existing appointment, freeing the slot for future bookings."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise ResourceNotFoundException("Appointment", appointment_id)

    if appointment.status == AppointmentStatus.CANCELLED.value:
        raise AppointmentAlreadyCancelledException("This appointment is already cancelled.")

    appointment.status = AppointmentStatus.CANCELLED.value
    appointment.cancellation_reason = reason.strip()
    db.commit()
    db.refresh(appointment)
    return appointment


def reschedule_appointment(
    db: Session,
    appointment_id: int,
    new_start_time: datetime,
    current_time: datetime | None = None
) -> Appointment:
    """Reschedules an active appointment to a new validated slot."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise ResourceNotFoundException("Appointment", appointment_id)

    if appointment.status == AppointmentStatus.CANCELLED.value:
        raise InvalidBookingException("Cannot reschedule an appointment that has been cancelled.")

    # Validate new slot while excluding the current appointment from collision checks
    normalized_new_start = validate_booking_time(
        db,
        appointment.doctor_id,
        new_start_time,
        current_time=current_time,
        exclude_appointment_id=appointment.id
    )
    new_end_time = normalized_new_start + timedelta(minutes=settings.SLOT_DURATION_MINUTES)

    appointment.start_time = normalized_new_start
    appointment.end_time = new_end_time

    try:
        db.commit()
        db.refresh(appointment)
    except IntegrityError:
        db.rollback()
        raise SlotConflictException("The requested new appointment slot is already taken.")

    return appointment
