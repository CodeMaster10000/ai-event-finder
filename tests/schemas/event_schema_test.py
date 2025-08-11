import pytest
from marshmallow import ValidationError
from app.schemas.event_schema import CreateEventSchema, EventSchema
from app.models.event import Event
from app.models.user import User

@pytest.fixture
def valid_payload():
    return {
        "title": "  Rock music event  ",
        "location": "  Beertija Pub, Skopje ",
        "description": " 20% discount on every beer between 8:00-900PM.    ",
        "category": "Rock",
        "datetime": "2025-07-31 20:30:00",
        "organizer_email": "bob@example.com",
    }


def test_create_event_schema_loads_and_normalizes(valid_payload):
    # Should trim whitespace and parse datetime
    data = CreateEventSchema().load(valid_payload)
    assert data["title"] == "Rock music event"
    assert data["location"] == "Beertija Pub, Skopje"
    assert data["description"] == "20% discount on every beer between 8:00-900PM."
    assert data["category"] == "Rock"
    assert str(data["datetime"]) == "2025-07-31 20:30:00"
    assert data["organizer_email"] == "bob@example.com"


def test_create_event_schema_rejects_extra_fields(valid_payload):
    payload = dict(valid_payload)
    payload["foo"] = "random"
    data = CreateEventSchema().load(payload)
    assert "foo" not in data


def test_dumped_guests_content(valid_payload):
    # After load, create an Event with guests and dump
    loaded = CreateEventSchema().load(valid_payload)
    organizer = User(id=1, name="Bob", surname="Smith", email="bob@example.com")
    event = Event(
        title=loaded["title"],
        location=loaded["location"],
        description=loaded["description"],
        category=loaded["category"],
        datetime=loaded["datetime"],
        organizer=organizer,
        organizer_id=organizer.id,
    )
    # Attach sample guests
    event.guests = [
        User(name=f"Guest{i}", surname=f"Test{i}", email=f"guest{i}@ex.com")
        for i in range(2)
    ]
    dumped = EventSchema().dump(event)
    assert isinstance(dumped["guests"], list)
    assert all(isinstance(g, dict) for g in dumped["guests"])


def test_dumped_datetime_string(valid_payload):
    loaded = CreateEventSchema().load(valid_payload)
    event = Event(
        title=loaded["title"],
        location=loaded["location"],
        description=loaded["description"],
        category=loaded["category"],
        datetime=loaded["datetime"],
        organizer=User(id=1, name="", surname="", email="bob@example.com"),
        organizer_id=1,
    )
    dumped = EventSchema().dump(event)
    assert dumped["datetime"] == "2025-07-31 20:30:00"


def test_create_event_schema_excludes_unknown_fields(valid_payload):
    payload = dict(valid_payload)
    payload["baz"] = 123
    data = CreateEventSchema().load(payload)
    assert "baz" not in data


def test_invalid_datetime_format(valid_payload):
    bad = dict(valid_payload)
    bad["datetime"] = "2025/07-31 20:30:00"
    with pytest.raises(ValidationError):
        CreateEventSchema().load(bad)
