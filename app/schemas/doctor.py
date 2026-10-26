from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict
from app.schemas.working_hours import WorkingHoursResponse


class DoctorBase(BaseModel):
    name: str
    specialty: str
    email: str


class DoctorResponse(DoctorBase):
    id: int
    is_active: bool
    created_at: datetime
    working_hours: List[WorkingHoursResponse] = []

    model_config = ConfigDict(from_attributes=True)


class DoctorAvailabilityResponse(BaseModel):
    doctor_id: int
    doctor_name: str
    date: str
    slot_duration_minutes: int
    available_slots: List[str]
