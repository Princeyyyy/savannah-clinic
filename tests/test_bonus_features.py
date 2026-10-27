from datetime import datetime, timedelta, timezone, date
from tests.test_availability import get_next_weekday
from app.services.availability import get_clinic_now


def test_upcoming_slot_bookable_without_arbitrary_cutoff(client):
    """
    Slots that have not passed are bookable right up until their start time.
    Slots in the past are rejected with HTTP 400.
    """
    future_thu = get_next_weekday(date.today(), target_weekday=3)
    slot_time = f"{future_thu.isoformat()}T10:00:00"

    res = client.post(
        "/api/v1/appointments",
        json={
            "doctor_id": 1,
            "patient_id": 1,
            "start_time": slot_time
        }
    )
    assert res.status_code == 201

    # Attempting to book a past slot returns HTTP 400
    past_time = "2020-01-02T10:00:00"
    past_res = client.post(
        "/api/v1/appointments",
        json={
            "doctor_id": 1,
            "patient_id": 1,
            "start_time": past_time
        }
    )
    assert past_res.status_code == 400
    assert "past" in past_res.json()["detail"].lower()


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
    assert appointments[0]["doctor_name"] is not None
    assert appointments[0]["patient_name"] == "John Kamau"

    # With upcoming_only=False, cancelled appointment is included
    all_res = client.get("/api/v1/patients/1/appointments?upcoming_only=false")
    assert all_res.status_code == 200
    assert len(all_res.json()) == 3


def test_doctor_availability_omitted_date_defaults_gracefully(client):
    """
    When the date query parameter is omitted in Swagger docs or API calls,
    the endpoint defaults to today (or next weekday) rather than failing with 422.
    """
    res = client.get("/api/v1/doctors/1/availability")
    assert res.status_code == 200
    data = res.json()
    assert "date" in data
    assert data["doctor_id"] == 1
    assert "available_slots" in data
    assert "all_slots" in data


def test_appointment_details_include_doctor_and_patient_names(client):
    """
    Ensure GET /appointments and GET /appointments/{id} populate
    doctor_name and patient_name rather than returning null.
    """
    future_mon = get_next_weekday(date.today(), target_weekday=0)
    slot = f"{future_mon.isoformat()}T14:00:00"

    book_res = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 2, "start_time": slot}
    )
    assert book_res.status_code == 201
    appt_id = book_res.json()["id"]

    get_one = client.get(f"/api/v1/appointments/{appt_id}")
    assert get_one.status_code == 200
    assert get_one.json()["doctor_name"] == "Dr. Joyce Moraa"
    assert get_one.json()["patient_name"] == "Faith Achieng"

    get_list = client.get("/api/v1/appointments")
    assert get_list.status_code == 200
    matching = [a for a in get_list.json() if a["id"] == appt_id]
    assert len(matching) == 1
    assert matching[0]["doctor_name"] == "Dr. Joyce Moraa"
    assert matching[0]["patient_name"] == "Faith Achieng"
