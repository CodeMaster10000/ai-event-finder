import pytest
from marshmallow import ValidationError

from app.models.event import Event
from app.models.user import User
from app.schemas.event_schema import (
    CreateEventSchema,
    EventSchema,
)

@pytest.fixture
def valid_payload():
    return {
        "title": "  Rock music event  ",
        "location": "  Beertija Pub, Skopje ",
        "description": " 20% discount on every beer between 8:00-900PM.    ",
        "category": "Rock",
        "datetime": "2025-07-31 20:30:00"
    }

def test_create_event_schema_loads_and_normalizes(valid_payload):
    data = CreateEventSchema().load(valid_payload)
    # leading/trailing whitespace stripped
    assert data["title"] == "Rock music event"
    assert data["location"] == "Beertija Pub, Skopje"
    assert data["description"] == "20% discount on every beer between 8:00-900PM."
    assert data["category"] == valid_payload["category"]


def test_create_event_schema_rejects_extra_fields(valid_payload):
    payload = dict(valid_payload, foo="random")
    data = CreateEventSchema().load(payload)
    # unknown fields are dropped
    assert "foo" not in data

def test_event_schema_dumps_only_public_fields():
    # event simulator dict
    event_obj = {
        "id": 1, # should be excluded
        "title": "Rock music event",
        "location": "Beertija Pub, Skopje",
        "description": "20% discount on every beer between 8:00-900PM.",
        "category": "Rock",
        "datetime": "2025-07-31 20:30:00",
        "organizer": {
            "id": 2,
            "name": "Bob",
            "surname": "Jones",
            "email": "bob@example.com",
            "password": "secret",  # should be excluded
            "created_at": "2025-01-01"  # should be excluded if not in UserSchema
        }
    }
    dumped = EventSchema().dump(event_obj)
    assert dumped == {
        "title": "Rock music event",
        "location": "Beertija Pub, Skopje",
        "description": "20% discount on every beer between 8:00-900PM.",
        "category": "Rock",
        "datetime": "2025-07-31 20:30:00",
        "organizer": {
            "name": "Bob",
            "surname": "Jones",
            "email": "bob@example.com"
        }
    }

@pytest.mark.parametrize("bad_datetime", [
    "2025-07-31",          # date only
    "31-07-2025 20:30:00", # wrong format
    "2025/07/31 20:30",    # slashes + no seconds
    "not-a-date"
])
def test_create_event_schema_rejects_bad_datetime(valid_payload, bad_datetime):
    payload = dict(valid_payload, datetime=bad_datetime)
    with pytest.raises(ValidationError) as ei:
        CreateEventSchema().load(payload)
    assert "datetime" in ei.value.messages

@pytest.mark.parametrize("missing_field", [
    "title", "location", "description", "category", "datetime"
])
def test_create_event_schema_requires_all_fields(valid_payload, missing_field):
    payload = dict(valid_payload)
    del payload[missing_field]

    with pytest.raises(ValidationError) as ei:
        CreateEventSchema().load(payload)
    assert missing_field in ei.value.messages

@pytest.mark.parametrize("empty_field", [
    "title", "location", "description", "category"
])
def test_create_event_schema_rejects_empty_strings(valid_payload, empty_field):
    payload = dict(valid_payload, **{empty_field: "   "})
    with pytest.raises(ValidationError) as ei:
        CreateEventSchema().load(payload)
    assert empty_field in ei.value.messages

def test_create_event_schema_rejects_too_long_title(valid_payload):
    payload = dict(valid_payload, title="a" * 100)  # exceeds TITLE_MAX_LENGTH
    with pytest.raises(ValidationError) as ei:
        CreateEventSchema().load(payload)
    assert "title" in ei.value.messages

def test_dumped_guests_content(valid_payload):
    """
    After round-trip, EventSchema.dump should serialize the 'guests'
    list into a list of dicts with only name & surname.
    """
    loaded = CreateEventSchema().load(valid_payload)
    # build event with 3 guests
    organizer = User(id=1, name="Org", surname="One", email="org@example.com")
    guests = [
        User(name=f"Guest{i}", surname=f"Surname{i}", email=f"g{i}@ex.com")
        for i in range(3)
    ]
    event = Event(
        title=loaded["title"],
        location=loaded["location"],
        description=loaded["description"],
        category=loaded["category"],
        datetime=loaded["datetime"],
        organizer=organizer,
        organizer_id=1,
    )
    event.guests = guests

    dumped = EventSchema().dump(event)
    # should be a list of dicts with exactly name & surname
    assert isinstance(dumped["guests"], list)
    assert all(isinstance(g, dict) for g in dumped["guests"])
    expected = [
        {"name": f"Guest{i}", "surname": f"Surname{i}"}
        for i in range(3)
    ]
    assert dumped["guests"] == expected

def test_dumped_datetime_string(valid_payload):
    """
    EventSchema.dump should output datetime as the same '%Y-%m-%d %H:%M:%S' string.
    """
    loaded = CreateEventSchema().load(valid_payload)
    organizer = User(id=1, name="Org", surname="One", email="org@example.com")
    event = Event(
        title=loaded["title"],
        location=loaded["location"],
        description=loaded["description"],
        category=loaded["category"],
        datetime=loaded["datetime"],
        organizer=organizer,
        organizer_id=1,
    )
    # no guests in this simple case
    dumped = EventSchema().dump(event)
    assert dumped["datetime"] == "2025-07-31 20:30:00"

def test_create_event_schema_excludes_unknown_fields(valid_payload):
    """
    CreateEventSchema should silently drop any extra keys (unknown=EXCLUDE).
    """
    extra = dict(valid_payload, foo="bar", baz=123)
    loaded = CreateEventSchema().load(extra)
    # none of the unknown keys should survive
    assert "foo" not in loaded
    assert "baz" not in loaded
    # and known keys still present & correct
    assert loaded["title"] == "Rock music event"
    assert loaded["location"].startswith("Beertija Pub")



