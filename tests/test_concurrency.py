import concurrent.futures
from datetime import date
from tests.test_availability import get_next_weekday


def test_concurrent_double_booking_prevention(client):
    """
    Stress test for race conditions:
    Simulate 10 concurrent requests attempting to book the exact same slot.
    Guarantees:
    - Exactly 1 request succeeds (HTTP 201 Created).
    - Exactly 9 requests are rejected (HTTP 409 Conflict).
    - Zero duplicate records in the database.
    """
    future_date = get_next_weekday(date.today(), target_weekday=4)
    target_slot = f"{future_date.isoformat()}T10:30:00"

    num_threads = 10
    responses = []

    def make_booking_request(patient_id: int):
        return client.post(
            "/api/v1/appointments",
            json={
                "doctor_id": 1,
                "patient_id": patient_id,
                "start_time": target_slot
            }
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Patient 1 and 2 alternative
        futures = [
            executor.submit(make_booking_request, (i % 2) + 1)
            for i in range(num_threads)
        ]
        for f in concurrent.futures.as_completed(futures):
            responses.append(f.result())

    success_responses = [r for r in responses if r.status_code == 201]
    conflict_responses = [r for r in responses if r.status_code == 409]

    assert len(success_responses) == 1, (
        f"Expected exactly 1 booking to succeed, but got {len(success_responses)}"
    )
    assert len(conflict_responses) == num_threads - 1, (
        f"Expected {num_threads - 1} bookings to be rejected with 409 Conflict, but got {len(conflict_responses)}"
    )

    # Double check availability endpoint reflects that slot is gone
    avail_res = client.get(f"/api/v1/doctors/1/availability?date={future_date.isoformat()}")
    assert target_slot not in avail_res.json()["available_slots"]
