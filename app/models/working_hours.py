from datetime import time
from sqlalchemy import Integer, Time, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class WorkingHours(Base):
    __tablename__ = "working_hours"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    # 0 = Monday, 1 = Tuesday, 2 = Wednesday, 3 = Thursday, 4 = Friday, 5 = Saturday, 6 = Sunday
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    break_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    break_end: Mapped[time | None] = mapped_column(Time, nullable=True)

    doctor = relationship("Doctor", back_populates="working_hours")
