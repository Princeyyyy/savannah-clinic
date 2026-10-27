from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PatientBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Patient full name", examples=["John Kamau"])
    email: str = Field(..., min_length=5, max_length=120, description="Patient email address", examples=["john.kamau@example.com"])
    phone: str = Field(..., min_length=7, max_length=30, description="Phone number with country code", examples=["+254712345678"])


class PatientCreate(PatientBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Jane Muthoni",
                "email": "jane.muthoni@example.com",
                "phone": "+254722123456"
            }
        }
    )


class PatientResponse(PatientBase):
    id: int = Field(..., description="Unique patient ID", examples=[1])
    created_at: datetime = Field(..., description="Registration timestamp")

    model_config = ConfigDict(from_attributes=True)
