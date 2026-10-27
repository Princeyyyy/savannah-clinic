from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.api.deps import get_db
from app.models import Doctor
from app.schemas.doctor import DoctorResponse, DoctorAvailabilityResponse, SlotDetail
from app.services.availability import get_doctor_schedule_slots, get_clinic_now
from app.core.config import settings

router = APIRouter()


@router.get("", response_model=List[DoctorResponse], summary="List all active doctors")
def list_doctors(db: Session = Depends(get_db)):
    """Retrieve all active doctors with their weekly working schedules."""
    doctors = (
        db.query(Doctor)
        .options(joinedload(Doctor.working_hours))
        .filter(Doctor.is_active.is_(True))
        .order_by(Doctor.id.asc())
        .all()
    )
    return doctors


@router.get(
    "/{id}/availability",
    response_model=DoctorAvailabilityResponse,
    summary="Get available 30-minute slots for a doctor on a given date"
)
def get_availability(
    id: int = Path(..., description="Doctor ID (e.g. 1)", examples=[1]),
    date_param: Optional[date] = Query(
        default=None,
        alias="date",
        description="Date to check availability (YYYY-MM-DD). If omitted, defaults to today or next clinic day.",
        examples=["2026-10-28"]
    ),
    db: Session = Depends(get_db)
):
    """
    Returns all available 30-minute slots for a doctor on a specified date.
    Also returns the complete schedule of all slots with statuses:
    - AVAILABLE: Open for booking
    - BOOKED: Already booked by a patient
    - BREAK: Doctor lunch break
    - PAST: Past slot in the day
    """
    doctor = db.query(Doctor).filter(Doctor.id == id, Doctor.is_active.is_(True)).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with identifier '{id}' was not found."
        )

    if date_param is None:
        clinic_today = get_clinic_now().date()
        # If Saturday (5) -> advance 2 days to Monday; if Sunday (6) -> advance 1 day to Monday
        if clinic_today.weekday() == 5:
            date_param = clinic_today + timedelta(days=2)
        elif clinic_today.weekday() == 6:
            date_param = clinic_today + timedelta(days=1)
        else:
            date_param = clinic_today

    available_slots, all_slots_details = get_doctor_schedule_slots(
        db=db,
        doctor_id=id,
        query_date=date_param
    )

    day_name = date_param.strftime("%A")
    message = None
    if not all_slots_details:
        message = f"{doctor.name} has no scheduled working hours on {day_name}."

    return DoctorAvailabilityResponse(
        doctor_id=doctor.id,
        doctor_name=doctor.name,
        date=date_param.isoformat(),
        slot_duration_minutes=settings.SLOT_DURATION_MINUTES,
        available_slots=[slot.isoformat() for slot in available_slots],
        all_slots=[SlotDetail(**slot_dict) for slot_dict in all_slots_details],
        message=message
    )
