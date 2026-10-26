from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models import Appointment
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentCancel,
    AppointmentReschedule,
    AppointmentResponse,
)
from app.services.booking import (
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
)

router = APIRouter()


def _format_appointment_response(appt: Appointment) -> AppointmentResponse:
    return AppointmentResponse(
        id=appt.id,
        doctor_id=appt.doctor_id,
        patient_id=appt.patient_id,
        start_time=appt.start_time,
        end_time=appt.end_time,
        status=appt.status,
        cancellation_reason=appt.cancellation_reason,
        created_at=appt.created_at,
        updated_at=appt.updated_at,
        doctor_name=appt.doctor.name if appt.doctor else None,
        patient_name=appt.patient.name if appt.patient else None,
    )


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book a 30-minute appointment slot"
)
def create_appointment(
    payload: AppointmentCreate,
    db: Session = Depends(get_db)
):
    """
    Book an appointment slot.
    Validations:
    - Within doctor's working hours & outside breaks
    - Not in the past
    - Minimum 1 hour in advance (Bonus requirement)
    - Slot is not already taken
    - Aligned with 30-minute intervals
    """
    appointment = book_appointment(
        db=db,
        doctor_id=payload.doctor_id,
        patient_id=payload.patient_id,
        start_time=payload.start_time
    )
    return _format_appointment_response(appointment)


@router.patch(
    "/{id}/cancel",
    response_model=AppointmentResponse,
    summary="Cancel an existing appointment"
)
def cancel(
    id: int,
    payload: AppointmentCancel,
    db: Session = Depends(get_db)
):
    """
    Cancel an appointment with a stated reason.
    The slot becomes immediately bookable again for other patients.
    Returns 400 Bad Request if the appointment is already cancelled.
    """
    appointment = cancel_appointment(
        db=db,
        appointment_id=id,
        reason=payload.reason
    )
    return _format_appointment_response(appointment)


@router.patch(
    "/{id}/reschedule",
    response_model=AppointmentResponse,
    summary="Reschedule an appointment to a new slot"
)
def reschedule(
    id: int,
    payload: AppointmentReschedule,
    db: Session = Depends(get_db)
):
    """
    Move an existing appointment to a new 30-minute slot.
    The original slot becomes available again, and the new slot is validated as a fresh booking.
    Returns 400 Bad Request if the appointment is already cancelled.
    Returns 409 Conflict if the target slot is taken.
    """
    appointment = reschedule_appointment(
        db=db,
        appointment_id=id,
        new_start_time=payload.new_start_time
    )
    return _format_appointment_response(appointment)


@router.get(
    "/{id}",
    response_model=AppointmentResponse,
    summary="Get appointment details by ID"
)
def get_appointment(
    id: int,
    db: Session = Depends(get_db)
):
    """Retrieve details for a single appointment."""
    appointment = db.query(Appointment).filter(Appointment.id == id).first()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with identifier '{id}' was not found."
        )
    return _format_appointment_response(appointment)


@router.get(
    "",
    response_model=List[AppointmentResponse],
    summary="List all appointments (optional filter by doctor or status)"
)
def list_appointments(
    doctor_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List appointments for admin or dashboard overview."""
    query = db.query(Appointment)
    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)
    if status_filter:
        query = query.filter(Appointment.status == status_filter.upper())
    appointments = query.order_by(Appointment.start_time.asc()).all()
    return [_format_appointment_response(appt) for appt in appointments]
