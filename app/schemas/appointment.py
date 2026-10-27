from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class AppointmentCreate(BaseModel):
    doctor_id: int = Field(
        ...,
        ge=1,
        description="ID of the doctor to book with (e.g. 1)",
        examples=[1]
    )
    patient_id: int = Field(
        ...,
        ge=1,
        description="ID of the patient booking the slot (e.g. 1)",
        examples=[1]
    )
    start_time: datetime = Field(
        ...,
        description="Appointment start time in ISO 8601 format, aligned to a 30-minute boundary (e.g. 2026-10-29T10:00:00)",
        examples=["2026-10-29T10:00:00"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "doctor_id": 1,
                "patient_id": 1,
                "start_time": "2026-10-29T10:00:00"
            }
        }
    )


class AppointmentCancel(BaseModel):
    reason: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Reason for cancellation",
        examples=["Patient requested cancellation due to work scheduling conflict"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reason": "Patient requested cancellation due to work scheduling conflict"
            }
        }
    )


class AppointmentReschedule(BaseModel):
    new_start_time: datetime = Field(
        ...,
        description="New appointment start time in ISO 8601 format aligned to a 30-minute boundary (e.g. 2026-10-29T14:00:00)",
        examples=["2026-10-29T14:00:00"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "new_start_time": "2026-10-29T14:00:00"
            }
        }
    )


class AppointmentResponse(BaseModel):
    id: int = Field(..., description="Unique appointment ID", examples=[1])
    doctor_id: int = Field(..., description="Assigned doctor ID", examples=[1])
    patient_id: int = Field(..., description="Booking patient ID", examples=[1])
    start_time: datetime = Field(..., description="Start timestamp of 30-minute slot")
    end_time: datetime = Field(..., description="End timestamp of 30-minute slot")
    status: str = Field(..., description="Booking status: BOOKED or CANCELLED", examples=["BOOKED"])
    cancellation_reason: str | None = Field(default=None, description="Reason if status is CANCELLED")
    created_at: datetime = Field(..., description="Timestamp when booking was created")
    updated_at: datetime = Field(..., description="Timestamp of last update")
    doctor_name: str | None = Field(default=None, description="Doctor full name", examples=["Dr. Joyce Moraa"])
    patient_name: str | None = Field(default=None, description="Patient full name", examples=["John Kamau"])

    model_config = ConfigDict(from_attributes=True)
