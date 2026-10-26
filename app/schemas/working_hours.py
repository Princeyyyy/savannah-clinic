from datetime import time
from pydantic import BaseModel, ConfigDict


class WorkingHoursResponse(BaseModel):
    id: int
    doctor_id: int
    day_of_week: int
    start_time: time
    end_time: time
    break_start: time | None = None
    break_end: time | None = None

    model_config = ConfigDict(from_attributes=True)
