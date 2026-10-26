import os
import pytest
from datetime import time
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.base import Base
from app.api.deps import get_db
from app.models import Doctor, WorkingHours, Patient

TEST_DB_FILE = Path("./test_clinic.db")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30.0},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def seed_test_data(db):
    # Seed 2 test doctors
    doc1 = Doctor(
        name="Dr. Joyce Moraa",
        specialty="General Practice",
        email="joyce.moraa@test.com",
        is_active=True
    )
    doc2 = Doctor(
        name="Dr. Kevin Otieno",
        specialty="Pediatrics",
        email="kevin.otieno@test.com",
        is_active=True
    )
    db.add_all([doc1, doc2])
    db.flush()

    # Mon-Fri (0-4) 09:00 - 17:00, lunch 13:00 - 14:00
    for doc in [doc1, doc2]:
        for day in range(5):
            wh = WorkingHours(
                doctor_id=doc.id,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(17, 0),
                break_start=time(13, 0),
                break_end=time(14, 0),
            )
            db.add(wh)

    # Seed 2 test patients
    pat1 = Patient(name="John Kamau", email="john.kamau@test.com", phone="+254712345678")
    pat2 = Patient(name="Faith Achieng", email="faith.achieng@test.com", phone="+254798765432")
    db.add_all([pat1, pat2])
    db.commit()


@pytest.fixture(scope="function")
def client():
    """Create a fresh database and provide isolated DB sessions per request."""
    Base.metadata.create_all(bind=test_engine)
    init_session = TestingSessionLocal()
    seed_test_data(init_session)
    init_session.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except Exception:
            pass
