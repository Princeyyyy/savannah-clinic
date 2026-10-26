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


def init_db():
    logger.info("Creating database tables if not present...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if doctors are already seeded
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
                db.flush()  # to obtain doctor.id

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

            for pat_data in INITIAL_PATIENTS:
                patient = Patient(
                    name=pat_data["name"],
                    email=pat_data["email"],
                    phone=pat_data["phone"]
                )
                db.add(patient)

            db.commit()
            logger.info("Successfully seeded doctors, working schedules, and sample patients.")
        else:
            logger.info("Database already seeded with %d doctors. Skipping seed.", existing_doctors)
    except Exception as e:
        logger.error("Error during database initialization: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
