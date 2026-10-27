from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.working_hours import WorkingHoursResponse


from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.working_hours import WorkingHoursResponse


class DoctorBase(BaseModel):
    name: str = Field(..., description="Doctor full name", examples=["Dr. Joyce Moraa"])
    specialty: str = Field(..., description="Medical specialty", examples=["General Practice"])
    email: str = Field(..., description="Professional email", examples=["joyce.moraa@savannahclinic.co.ke"])


class DoctorResponse(DoctorBase):
    id: int = Field(..., description="Doctor ID", examples=[1])
    is_active: bool = Field(..., description="Whether doctor is active", examples=[True])
    created_at: datetime = Field(..., description="Creation timestamp")
    working_hours: List[WorkingHoursResponse] = Field(default=[], description="Weekly working schedules")

    model_config = ConfigDict(from_attributes=True)


class SlotDetail(BaseModel):
    start_time: str = Field(..., description="Slot start time in ISO 8601", examples=["2026-10-28T09:00:00"])
    end_time: str = Field(..., description="Slot end time in ISO 8601", examples=["2026-10-28T09:30:00"])
    status: str = Field(..., description="Status: AVAILABLE, BOOKED, BREAK, CUTOFF, or PAST", examples=["AVAILABLE"])
    label: str = Field(..., description="Readable time range label", examples=["09:00 AM - 09:30 AM"])
    appointment_id: Optional[int] = Field(default=None, description="Associated appointment ID if booked")
    patient_name: Optional[str] = Field(default=None, description="Patient name if booked")


class DoctorAvailabilityResponse(BaseModel):
    doctor_id: int = Field(..., description="Doctor ID", examples=[1])
    doctor_name: str = Field(..., description="Doctor full name", examples=["Dr. Joyce Moraa"])
    date: str = Field(..., description="Date queried (YYYY-MM-DD)", examples=["2026-10-28"])
    slot_duration_minutes: int = Field(..., description="Slot interval duration in minutes", examples=[30])
    available_slots: List[str] = Field(
        ...,
        description="List of available slot start timestamps open for booking",
        examples=[["2026-10-28T09:00:00", "2026-10-28T09:30:00"]]
    )
    all_slots: List[SlotDetail] = Field(
        default=[],
        description="Comprehensive list of all slots across the day with color/status indicators"
    )
    message: Optional[str] = Field(
        default=None,
        description="Contextual note if doctor has no hours or special schedule for the date"
    )
