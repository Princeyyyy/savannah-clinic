from datetime import date, timedelta
from tests.test_availability import get_next_weekday


def test_book_appointment_success(client):
    """Booking a valid slot returns 201 Created and correct appointment fields."""
    future_tue = get_next_weekday(date.today(), target_weekday=1)
    slot_time = f"{future_tue.isoformat()}T09:30:00"

    response = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot_time}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["doctor_id"] == 1
    assert data["patient_id"] == 1
    assert data["status"] == "BOOKED"
    assert "T09:30:00" in data["start_time"]
    assert "T10:00:00" in data["end_time"]
    assert data["cancellation_reason"] is None


def test_book_appointment_double_booking_rejection(client):
    """Attempting to book an already reserved slot returns HTTP 409 Conflict."""
    future_tue = get_next_weekday(date.today(), target_weekday=1)
    slot_time = f"{future_tue.isoformat()}T11:00:00"

    # First booking
    res1 = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot_time}
    )
    assert res1.status_code == 201

    # Second booking for same doctor and slot
    res2 = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 2, "start_time": slot_time}
    )
    assert res2.status_code == 409
    assert "already taken" in res2.json()["detail"].lower()


def test_book_appointment_outside_working_hours(client):
    """Times before 09:00 or at/after 17:00 must be rejected with HTTP 400."""
    future_tue = get_next_weekday(date.today(), target_weekday=1)

    # 08:30 (before opening)
    res_early = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": f"{future_tue.isoformat()}T08:30:00"}
    )
    assert res_early.status_code == 400
    assert "working hours" in res_early.json()["detail"].lower()

    # 17:00 (end of workday, 30m slot would end at 17:30)
    res_late = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": f"{future_tue.isoformat()}T17:00:00"}
    )
    assert res_late.status_code == 400
    assert "working hours" in res_late.json()["detail"].lower()


def test_book_appointment_during_lunch_break(client):
    """Booking at 13:00 or 13:30 must be rejected because it is doctor's lunch break."""
    future_tue = get_next_weekday(date.today(), target_weekday=1)

    res = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": f"{future_tue.isoformat()}T13:00:00"}
    )
    assert res.status_code == 400
    assert "break" in res.json()["detail"].lower()


def test_book_appointment_in_the_past(client):
    """Booking a date/time in the past returns HTTP 400."""
    res = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": "2020-01-06T10:00:00"}
    )
    assert res.status_code == 400
    assert "past" in res.json()["detail"].lower()


def test_book_appointment_unaligned_slot(client):
    """Slot not aligned on 30-min boundaries (e.g. 10:15) returns HTTP 400."""
    future_tue = get_next_weekday(date.today(), target_weekday=1)
    res = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": f"{future_tue.isoformat()}T10:15:00"}
    )
    assert res.status_code == 400
    assert "30-minute" in res.json()["detail"].lower()


def test_book_appointment_invalid_doctor_or_patient(client):
    """Non-existent doctor or patient returns HTTP 404."""
    future_tue = get_next_weekday(date.today(), target_weekday=1)
    slot_time = f"{future_tue.isoformat()}T10:00:00"

    res_doc = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 9999, "patient_id": 1, "start_time": slot_time}
    )
    assert res_doc.status_code == 404

    res_pat = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 9999, "start_time": slot_time}
    )
    assert res_pat.status_code == 404
