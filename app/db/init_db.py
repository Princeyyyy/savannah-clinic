import logging
from datetime import time
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models import Doctor, WorkingHours, Patient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INITIAL_DOCTORS = [
    {
        "name": "Dr. Joyce Moraa",
        "specialty": "General Practice",
        "email": "joyce.moraa@savannahclinic.co.ke",
    },
    {
        "name": "Dr. Kevin Otieno",
        "specialty": "Pediatrics",
        "email": "kevin.otieno@savannahclinic.co.ke",
    },
    {
        "name": "Dr. Amina Hassan",
        "specialty": "Internal Medicine",
        "email": "amina.hassan@savannahclinic.co.ke",
    },
    {
        "name": "Dr. Brian Mutua",
        "specialty": "Cardiology",
        "email": "brian.mutua@savannahclinic.co.ke",
    },
    {
        "name": "Dr. Grace Wanjiku",
        "specialty": "Dermatology",
        "email": "grace.wanjiku@savannahclinic.co.ke",
    },
]

INITIAL_PATIENTS = [
    {
        "name": "John Kamau",
        "email": "john.kamau@example.com",
        "phone": "+254712345678"
    },
    {
        "name": "Faith Achieng",
        "email": "faith.achieng@example.com",
        "phone": "+254798765432"
    }
]


import logging
from datetime import date, time, timedelta
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models import Doctor, WorkingHours, Patient, Appointment, AppointmentStatus
from app.services.availability import get_clinic_now

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INITIAL_DOCTORS = [
    {
        "name": "Dr. Joyce Moraa",
        "specialty": "General Practice",
        "email": "joyce.moraa@savannahclinic.co.ke",
    },
    {
        "name": "Dr. Kevin Otieno",
        "specialty": "Pediatrics",
        "email": "kevin.otieno@savannahclinic.co.ke",
    },
    {
        "name": "Dr. Amina Hassan",
        "specialty": "Internal Medicine",
        "email": "amina.hassan@savannahclinic.co.ke",
    },
    {
        "name": "Dr. Brian Mutua",
        "specialty": "Cardiology",
        "email": "brian.mutua@savannahclinic.co.ke",
    },
    {
        "name": "Dr. Grace Wanjiku",
        "specialty": "Dermatology",
        "email": "grace.wanjiku@savannahclinic.co.ke",
    },
]

INITIAL_PATIENTS = [
    {
        "name": "John Kamau",
        "email": "john.kamau@example.com",
        "phone": "+254712345678"
    },
    {
        "name": "Faith Achieng",
        "email": "faith.achieng@example.com",
        "phone": "+254798765432"
    },
    {
        "name": "Jane Muthoni",
        "email": "jane.muthoni@example.com",
        "phone": "+254722123456"
    }
]


def get_next_weekday(start_date: date) -> date:
    """Returns the next calendar weekday (Monday-Friday) after start_date."""
    d = start_date + timedelta(days=1)
    while d.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
        d += timedelta(days=1)
    return d


def init_db():
    logger.info("Creating database tables if not present...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Step 1: Ensure initial 5 doctors and weekly working schedules exist
        existing_doctors = db.query(Doctor).count()
        if existing_doctors == 0:
            logger.info("Seeding initial 5 doctors and working hours...")
            for doc_data in INITIAL_DOCTORS:
                doctor = Doctor(
                    name=doc_data["name"],
                    specialty=doc_data["specialty"],
                    email=doc_data["email"],
                    is_active=True
                )
                db.add(doctor)
                db.flush()

                # Working hours: Monday (0) through Friday (4) from 09:00 to 17:00, lunch 13:00 to 14:00
                for day in range(5):
                    wh = WorkingHours(
                        doctor_id=doctor.id,
                        day_of_week=day,
                        start_time=time(9, 0),
                        end_time=time(17, 0),
                        break_start=time(13, 0),
                        break_end=time(14, 0),
                    )
                    db.add(wh)
            db.commit()
            logger.info("Successfully seeded 5 doctors and working hours.")
        else:
            logger.info("Database has %d doctors present.", existing_doctors)

        # Step 2: Ensure initial patients exist
        for pat_data in INITIAL_PATIENTS:
            existing_pat = db.query(Patient).filter(Patient.email == pat_data["email"]).first()
            if not existing_pat:
                db.add(Patient(
                    name=pat_data["name"],
                    email=pat_data["email"],
                    phone=pat_data["phone"]
                ))
        db.commit()

        # Step 3: Ensure upcoming sample appointments exist for docs testing
        clinic_now = get_clinic_now()
        upcoming_count = db.query(Appointment).filter(
            Appointment.start_time >= clinic_now,
            Appointment.status == AppointmentStatus.BOOKED.value
        ).count()

        if upcoming_count == 0:
            logger.info("Seeding upcoming sample appointments for interactive testing...")
            doc1 = db.query(Doctor).filter(Doctor.id == 1).first()
            doc2 = db.query(Doctor).filter(Doctor.id == 2).first()
            pat1 = db.query(Patient).filter(Patient.id == 1).first()
            pat2 = db.query(Patient).filter(Patient.id == 2).first()

            if doc1 and doc2 and pat1 and pat2:
                next_day_1 = get_next_weekday(clinic_now.date())
                next_day_2 = get_next_weekday(next_day_1)

                from datetime import datetime
                # Appointment 1: Booked upcoming slot for Patient 1 with Doctor 1 (10:00 AM)
                appt1 = Appointment(
                    doctor_id=doc1.id,
                    patient_id=pat1.id,
                    start_time=datetime.combine(next_day_1, time(10, 0)),
                    end_time=datetime.combine(next_day_1, time(10, 30)),
                    status=AppointmentStatus.BOOKED.value
                )
                # Appointment 2: Booked upcoming slot for Patient 2 with Doctor 1 (2:30 PM)
                appt2 = Appointment(
                    doctor_id=doc1.id,
                    patient_id=pat2.id,
                    start_time=datetime.combine(next_day_1, time(14, 30)),
                    end_time=datetime.combine(next_day_1, time(15, 0)),
                    status=AppointmentStatus.BOOKED.value
                )
                # Appointment 3: Booked upcoming slot for Patient 1 with Doctor 2 (11:00 AM on next_day_2)
                appt3 = Appointment(
                    doctor_id=doc2.id,
                    patient_id=pat1.id,
                    start_time=datetime.combine(next_day_2, time(11, 0)),
                    end_time=datetime.combine(next_day_2, time(11, 30)),
                    status=AppointmentStatus.BOOKED.value
                )
                # Appointment 4: Cancelled slot for Patient 1 with Doctor 1 (demonstrating cancellation reason)
                appt4 = Appointment(
                    doctor_id=doc1.id,
                    patient_id=pat1.id,
                    start_time=datetime.combine(next_day_1, time(9, 30)),
                    end_time=datetime.combine(next_day_1, time(10, 0)),
                    status=AppointmentStatus.CANCELLED.value,
                    cancellation_reason="Patient requested schedule change due to personal conflict"
                )

                db.add_all([appt1, appt2, appt3, appt4])
                db.commit()
                logger.info("Successfully seeded upcoming sample appointments.")

    except Exception as e:
        logger.error("Error during database initialization: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
