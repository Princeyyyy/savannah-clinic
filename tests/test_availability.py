from datetime import date, timedelta


def get_next_weekday(start_date: date, target_weekday: int = 2) -> date:
    """Returns the next occurrence of a given weekday (0=Mon, 2=Wed, etc.) at least 7 days ahead."""
    d = start_date + timedelta(days=7)
    while d.weekday() != target_weekday:
        d += timedelta(days=1)
    return d


def test_doctor_availability_weekday_slots(client):
    """A standard weekday (9am-5pm minus 1pm-2pm lunch) must yield exactly 14 30-min slots."""
    future_wednesday = get_next_weekday(date.today(), target_weekday=2)
    response = client.get(f"/api/v1/doctors/1/availability?date={future_wednesday.isoformat()}")

    assert response.status_code == 200
    data = response.json()
    assert data["doctor_id"] == 1
    assert data["date"] == future_wednesday.isoformat()
    assert data["slot_duration_minutes"] == 30

    slots = data["available_slots"]
    # 9:00 to 13:00 = 8 slots (09:00, 09:30, 10:00, 10:30, 11:00, 11:30, 12:00, 12:30)
    # 14:00 to 17:00 = 6 slots (14:00, 14:30, 15:00, 15:30, 16:00, 16:30)
    # Total = 14 slots
    assert len(slots) == 14

    # Verify no slots fall between 13:00 and 14:00 (lunch break)
    for slot_iso in slots:
        assert "T13:00:00" not in slot_iso
        assert "T13:30:00" not in slot_iso


def test_doctor_availability_weekend(client):
    """Doctor working hours are Mon-Fri, so weekends must return zero slots."""
    future_sunday = get_next_weekday(date.today(), target_weekday=6)
    response = client.get(f"/api/v1/doctors/1/availability?date={future_sunday.isoformat()}")

    assert response.status_code == 200
    data = response.json()
    assert len(data["available_slots"]) == 0


def test_doctor_availability_non_existent_doctor(client):
    """Querying availability for an invalid doctor ID returns 404."""
    future_date = date.today() + timedelta(days=5)
    response = client.get(f"/api/v1/doctors/9999/availability?date={future_date.isoformat()}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_booked_slot_removed_from_availability(client):
    """Once booked, that slot must not be available in the availability endpoint."""
    future_wednesday = get_next_weekday(date.today(), target_weekday=2)
    slot_time = f"{future_wednesday.isoformat()}T10:00:00"

    # Book slot
    book_res = client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot_time}
    )
    assert book_res.status_code == 201

    # Check availability
    avail_res = client.get(f"/api/v1/doctors/1/availability?date={future_wednesday.isoformat()}")
    assert avail_res.status_code == 200
    available_slots = avail_res.json()["available_slots"]

    assert slot_time not in available_slots
    assert len(available_slots) == 13


def test_doctor_schedule_all_slots_statuses(client):
    """Verify that all_slots categorizes booked slots as BOOKED and free slots as AVAILABLE."""
    future_wednesday = get_next_weekday(date.today(), target_weekday=2)
    slot_time = f"{future_wednesday.isoformat()}T10:00:00"

    # Book 1 slot
    client.post(
        "/api/v1/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot_time}
    )

    avail_res = client.get(f"/api/v1/doctors/1/availability?date={future_wednesday.isoformat()}")
    data = avail_res.json()
    all_slots = data["all_slots"]

    # Locate the booked slot
    booked_slot = next((s for s in all_slots if s["start_time"] == slot_time), None)
    assert booked_slot is not None
    assert booked_slot["status"] == "BOOKED"
    assert booked_slot["patient_name"] == "John Kamau"

    # Locate an open slot
    open_slot = next((s for s in all_slots if s["start_time"] == f"{future_wednesday.isoformat()}T09:00:00"), None)
    assert open_slot is not None
    assert open_slot["status"] == "AVAILABLE"

    # Locate lunch break slot
    break_slot = next((s for s in all_slots if s["start_time"] == f"{future_wednesday.isoformat()}T13:00:00"), None)
    assert break_slot is not None
    assert break_slot["status"] == "BREAK"
