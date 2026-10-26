from datetime import datetime, timedelta, timezone, date
from tests.test_availability import get_next_weekday
from app.services.availability import get_clinic_now


def test_bonus_prevention_of_bookings_within_one_hour(client):
    """
    Prevention of bookings within 1 hour of now.
    A slot starting 30 minutes from now must be rejected with HTTP 400.
    """
    clinic_now = get_clinic_now()
    # Target 30 minutes in the future, rounded to 30m boundary
    minute = 30 if clinic_now.minute < 30 else 0
    target_dt = (clinic_now + timedelta(minutes=30)).replace(minute=minute, second=0, microsecond=0)
    if target_dt <= clinic_now:
        target_dt += timedelta(minutes=30)

    # If within 1 hour of now
    time_diff = (target_dt - clinic_now).total_seconds() / 3600
    if time_diff < 1.0:
        res = client.post(
            "/api/v1/appointments",
            json={
                "doctor_id": 1,
                "patient_id": 1,
                "start_time": target_dt.strftime("%Y-%m-%dT%H:%M:%S")
            }
        )
        assert res.status_code == 400
        assert "at least 1 hour" in res.json()["detail"].lower() or "working hours" in res.json()["detail"].lower()


def test_bonus_patient_upcoming_appointments_sorted(client):
    """
    Bonus requirement: GET /patients/{id}/appointments — upcoming appointments sorted chronologically.
    """
    future_mon = get_next_weekday(date.today(), target_weekday=0)
    slot1 = f"{future_mon.isoformat()}T11:00:00"
    slot2 = f"{future_mon.isoformat()}T09:30:00"
    slot3 = f"{future_mon.isoformat()}T15:00:00"

    # Book 3 appointments for patient 1 out of order (slot1, slot2, slot3)
    client.post("/api/v1/appointments", json={"doctor_id": 1, "patient_id": 1, "start_time": slot1})
    client.post("/api/v1/appointments", json={"doctor_id": 2, "patient_id": 1, "start_time": slot2})
    res3 = client.post("/api/v1/appointments", json={"doctor_id": 1, "patient_id": 1, "start_time": slot3})
    appt3_id = res3.json()["id"]

    # Cancel slot3
    client.patch(f"/api/v1/appointments/{appt3_id}/cancel", json={"reason": "Cancelled by patient"})

    # Fetch patient's upcoming appointments
    response = client.get("/api/v1/patients/1/appointments")
    assert response.status_code == 200
    appointments = response.json()

    # Cancelled appointment should not appear in active upcoming appointments
    assert len(appointments) == 2

    # Must be sorted chronologically: 09:30 before 11:00
    assert "T09:30:00" in appointments[0]["start_time"]
    assert "T11:00:00" in appointments[1]["start_time"]
