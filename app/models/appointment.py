from enum import Enum
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now


class AppointmentStatus(str, Enum):
    BOOKED = "BOOKED"
    CANCELLED = "CANCELLED"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=AppointmentStatus.BOOKED.value, nullable=False)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    doctor = relationship("Doctor", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")

    __table_args__ = (
        Index(
            "uq_active_doctor_slot",
            "doctor_id",
            "start_time",
            unique=True,
            sqlite_where=text("status = 'BOOKED'"),
            postgresql_where=text("status = 'BOOKED'"),
        ),
    )
