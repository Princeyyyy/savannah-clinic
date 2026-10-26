from datetime import date
from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models import Doctor
from app.schemas.doctor import DoctorResponse, DoctorAvailabilityResponse
from app.services.availability import get_doctor_available_slots
from app.core.config import settings

router = APIRouter()


@router.get("", response_model=List[DoctorResponse], summary="List all active doctors")
def list_doctors(db: Session = Depends(get_db)):
    """Retrieve all active doctors with their weekly working schedules."""
    doctors = db.query(Doctor).filter(Doctor.is_active.is_(True)).all()
    return doctors


@router.get(
    "/{id}/availability",
    response_model=DoctorAvailabilityResponse,
    summary="Get available 30-minute slots for a doctor on a given date"
)
def get_availability(
    id: int,
    date_param: date = Query(..., alias="date", description="Date to check availability (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Returns all available 30-minute slots for a doctor on a specified date.
    Excludes past slots, lunch breaks, slots within 1 hour cutoff, and existing bookings.
    """
    doctor = db.query(Doctor).filter(Doctor.id == id, Doctor.is_active.is_(True)).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with identifier '{id}' was not found."
        )

    slots = get_doctor_available_slots(db=db, doctor_id=id, query_date=date_param)
    
    return DoctorAvailabilityResponse(
        doctor_id=doctor.id,
        doctor_name=doctor.name,
        date=date_param.isoformat(),
        slot_duration_minutes=settings.SLOT_DURATION_MINUTES,
        available_slots=[slot.isoformat() for slot in slots]
    )
