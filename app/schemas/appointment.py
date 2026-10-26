from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class AppointmentCreate(BaseModel):
    doctor_id: int = Field(..., description="ID of the doctor to book with")
    patient_id: int = Field(..., description="ID of the patient booking the slot")
    start_time: datetime = Field(..., description="Appointment start time (ISO 8601, 30-min boundary)")


class AppointmentCancel(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500, description="Reason for cancellation")


class AppointmentReschedule(BaseModel):
    new_start_time: datetime = Field(..., description="New appointment start time (ISO 8601, 30-min boundary)")


class AppointmentResponse(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    start_time: datetime
    end_time: datetime
    status: str
    cancellation_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    doctor_name: str | None = None
    patient_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
