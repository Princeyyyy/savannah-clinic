from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models import Patient, Appointment, AppointmentStatus
from app.schemas.patient import PatientResponse, PatientCreate
from app.schemas.appointment import AppointmentResponse
from app.api.v1.endpoints.appointments import _format_appointment_response

router = APIRouter()


@router.get("", response_model=List[PatientResponse], summary="List all registered patients")
def list_patients(db: Session = Depends(get_db)):
    """Retrieve all patients registered in the clinic."""
    patients = db.query(Patient).all()
    return patients


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED, summary="Register a new patient")
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    """Register a new patient."""
    existing = db.query(Patient).filter(Patient.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Patient with email '{payload.email}' already exists."
        )
    patient = Patient(
        name=payload.name,
        email=payload.email,
        phone=payload.phone
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get(
    "/{id}/appointments",
    response_model=List[AppointmentResponse],
    summary="[Bonus] Get upcoming appointments for a patient sorted chronologically"
)
def get_patient_upcoming_appointments(
    id: int,
    db: Session = Depends(get_db)
):
    """
    Returns upcoming appointments for the given patient:
    - start_time >= current UTC time
    - Sorted chronologically (start_time ASC)
    """
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{id}' was not found."
        )

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    appointments = db.query(Appointment).filter(
        Appointment.patient_id == id,
        Appointment.start_time >= now_utc,
        Appointment.status == AppointmentStatus.BOOKED.value
    ).order_by(Appointment.start_time.asc()).all()

    return [_format_appointment_response(appt) for appt in appointments]
