from datetime import date
from tests.test_availability import get_next_weekday


def test_cancel_appointment_and_rebook(client):
    """
    Cancelling an appointment sets status to CANCELLED and records reason.
    The slot must immediately become bookable again by another patient.
    """
    future_thu = get_next_weekday(date.today(), target_weekday=3)
    slot_time = f"{future_thu.isoformat()}T11:30:00"

    # Step 1: Book slot
    book_res = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot_time}
    )
    assert book_res.status_code == 201
    appt_id = book_res.json()["id"]

    # Step 2: Cancel appointment
    cancel_res = client.patch(
        f"/api/v1/appointments/{appt_id}/cancel",
        json={"reason": "Patient is travelling abroad"}
    )
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()
    assert cancel_data["status"] == "CANCELLED"
    assert cancel_data["cancellation_reason"] == "Patient is travelling abroad"

    # Step 3: Verify slot is available again and can be booked by patient 2
    rebook_res = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 2, "start_time": slot_time}
    )
    assert rebook_res.status_code == 201
    assert rebook_res.json()["patient_id"] == 2
    assert rebook_res.json()["status"] == "BOOKED"


def test_cancel_already_cancelled_appointment(client):
    """Attempting to cancel an already cancelled appointment must return HTTP 400."""
    future_thu = get_next_weekday(date.today(), target_weekday=3)
    slot_time = f"{future_thu.isoformat()}T14:30:00"

    book_res = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot_time}
    )
    appt_id = book_res.json()["id"]

    # First cancel
    client.patch(f"/api/v1/appointments/{appt_id}/cancel", json={"reason": "Schedule clash"})

    # Second cancel must fail
    res_again = client.patch(f"/api/v1/appointments/{appt_id}/cancel", json={"reason": "Duplicate cancel"})
    assert res_again.status_code == 400
    assert "already" in res_again.json()["detail"].lower()


def test_reschedule_appointment_success(client):
    """Rescheduling updates start_time and end_time, and releases the previous slot."""
    future_thu = get_next_weekday(date.today(), target_weekday=3)
    slot_old = f"{future_thu.isoformat()}T09:00:00"
    slot_new = f"{future_thu.isoformat()}T10:00:00"

    # Book slot_old
    book_res = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot_old}
    )
    appt_id = book_res.json()["id"]

    # Reschedule to slot_new
    resched_res = client.patch(
        f"/api/v1/appointments/{appt_id}/reschedule",
        json={"new_start_time": slot_new}
    )
    assert resched_res.status_code == 200
    assert "T10:00:00" in resched_res.json()["start_time"]
    assert "T10:30:00" in resched_res.json()["end_time"]

    # Old slot must now be available and bookable by someone else
    rebook_old = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 2, "start_time": slot_old}
    )
    assert rebook_old.status_code == 201


def test_reschedule_to_occupied_slot(client):
    """Rescheduling to a slot that is already taken by another booking returns 409 Conflict."""
    future_thu = get_next_weekday(date.today(), target_weekday=3)
    slot1 = f"{future_thu.isoformat()}T09:00:00"
    slot2 = f"{future_thu.isoformat()}T09:30:00"

    # Patient 1 books slot 1
    res1 = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot1}
    )
    appt1_id = res1.json()["id"]

    # Patient 2 books slot 2
    client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 2, "start_time": slot2}
    )

    # Patient 1 tries to reschedule to slot 2 (which is occupied)
    conflict_res = client.patch(
        f"/api/v1/appointments/{appt1_id}/reschedule",
        json={"new_start_time": slot2}
    )
    assert conflict_res.status_code == 409
    assert "already taken" in conflict_res.json()["detail"].lower()


def test_reschedule_cancelled_appointment(client):
    """Attempting to reschedule an already cancelled appointment returns HTTP 400."""
    future_thu = get_next_weekday(date.today(), target_weekday=3)
    slot1 = f"{future_thu.isoformat()}T15:00:00"
    slot2 = f"{future_thu.isoformat()}T15:30:00"

    book_res = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot1}
    )
    appt_id = book_res.json()["id"]

    # Cancel it
    client.patch(f"/api/v1/appointments/{appt_id}/cancel", json={"reason": "No longer needed"})

    # Try to reschedule
    resched_res = client.patch(
        f"/api/v1/appointments/{appt_id}/reschedule",
        json={"new_start_time": slot2}
    )
    assert resched_res.status_code == 400
    assert "cancelled" in resched_res.json()["detail"].lower()
