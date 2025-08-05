import pytest
from marshmallow import ValidationError
from app.models.user import User

# 1. Import your schemas
from app.schemas.event_schema import CreateEventSchema, EventSchema

# 2. Import your model
from app.models.event import Event

@pytest.fixture
def raw_payload():
    return {
        "title": "  Rock music event  ",
        "location": "  Beertija Pub, Skopje ",
        "description": " 20% discount on every beer between 8:00-900PM.    ",
        "category": "Rock",
        "datetime": "2025-07-31 20:30:00",
        "organizer_email": "bob@example.com",
    }

# Roundtrip: DTO -> Entity -> DTO
def test_dto_to_entity_to_dto_roundtrip(raw_payload):
    # 1) LOAD: Validate & normalize incoming data
    loaded = CreateEventSchema().load(raw_payload)

    # verify organizer_email is present in loaded data
    assert loaded["organizer_email"] == raw_payload["organizer_email"]

    # 2) Creating a mock user and guests list
    organizer = User(id=2, name="Bob", surname="Jones", email="bob@example.com")
    guests = [
        User(name=f"Name {i}", surname=f"Surname {i}", email=f"email{i}@example.com")
        for i in range(3)
    ]
    # 3) DTO -> Entity: attach dummy organizer_id and build Event
    event = Event(
        title=loaded["title"],
        location=loaded["location"],
        description=loaded["description"],
        category=loaded["category"],
        datetime=loaded["datetime"],
        organizer=organizer,
        organizer_id=organizer.id,
    )
    event.guests = guests

    # 4) DUMP: serialize back to dict
    dumped = EventSchema().dump(event)

    # 5) ASSERTIONS: loaded values trimmed and normalized
    assert loaded["title"] == "Rock music event"
    assert loaded["location"] == "Beertija Pub, Skopje"
    assert loaded["description"] == "20% discount on every beer between 8:00-900PM."
    assert loaded["category"] == "Rock"
    assert str(loaded["datetime"]) == "2025-07-31 20:30:00"

    # check that 'organizer' is present and correctly serialized
    assert isinstance(dumped["organizer"], dict)
    assert dumped["organizer"] == {
        "name": "Bob",
        "surname": "Jones",
        "email": "bob@example.com"
    }

    # ensure guests were serialized
    assert isinstance(dumped["guests"], list)
    assert len(dumped["guests"]) == 3

    # check keys
    assert set(dumped.keys()) == {
        "title", "location", "description", "category", "datetime", "organizer", "guests"
    }


def test_invalid_datetime_format():
    bad = {
        "title": "Rock music event",
        "location": "Beertija Pub, Skopje",
        "description": "20% discount on every beer between 8:00-900PM.",
        "category": "Rock",
        "datetime": "2025/07-31 20:30:00",
        "organizer_email": "bob@example.com",
    }
    with pytest.raises(ValidationError):
        CreateEventSchema().load(bad)
