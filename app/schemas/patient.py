from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PatientBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=120)
    phone: str = Field(..., min_length=7, max_length=30)


class PatientCreate(PatientBase):
    pass


class PatientResponse(PatientBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
