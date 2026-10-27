from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session, joinedload
from app.api.deps import get_db
from app.models import Patient, Appointment, AppointmentStatus
from app.schemas.patient import PatientResponse, PatientCreate
from app.schemas.appointment import AppointmentResponse
from app.api.v1.endpoints.appointments import _format_appointment_response
from app.services.availability import get_clinic_now

router = APIRouter()


@router.get("", response_model=List[PatientResponse], summary="List all registered patients")
def list_patients(db: Session = Depends(get_db)):
    """Retrieve all patients registered in the clinic."""
    patients = db.query(Patient).order_by(Patient.id.asc()).all()
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
    summary="Get upcoming appointments for a patient sorted chronologically"
)
def get_patient_upcoming_appointments(
    id: int = Path(..., description="Patient ID (e.g. 1)", examples=[1]),
    upcoming_only: bool = Query(
        default=True,
        description="Filter for upcoming appointments only (default: true). Set to false to view all historical and cancelled appointments."
    ),
    db: Session = Depends(get_db)
):
    """
    Returns upcoming appointments for the given patient:
    - start_time >= current clinic time (Africa/Nairobi)
    - Sorted chronologically (start_time ASC)
    - Optionally includes historical or cancelled appointments when upcoming_only=false
    """
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{id}' was not found."
        )

    clinic_now = get_clinic_now()

    query = (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor), joinedload(Appointment.patient))
        .filter(Appointment.patient_id == id)
    )

    if upcoming_only:
        query = query.filter(
            Appointment.start_time >= clinic_now,
            Appointment.status == AppointmentStatus.BOOKED.value
        )

    appointments = query.order_by(Appointment.start_time.asc()).all()

    return [_format_appointment_response(appt) for appt in appointments]
