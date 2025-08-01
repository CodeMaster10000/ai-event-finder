import pytest
from marshmallow import ValidationError
from app.models.user import User

# 1. Import your schemas
from app.schemas.event_schema import CreateEventSchema, EventSchema

# 2. Import your model/
from app.models.event import Event

# 3. A dummy hash function (replace with your real one or mock)
def dummy_hash(raw):
    return f"hashed-{raw}"

@pytest.fixture
def raw_payload():
    return {
        "title": "  Rock music event  ",
        "location": "  Beertija Pub, Skopje ",
        "description": " 20% discount on every beer between 8:00-900PM.    ",
        "category": "Rock",
        "datetime": "2025-07-31 20:30:00",
    }

def test_dto_to_entity_to_dto_roundtrip(raw_payload):
    # 1) LOAD: Validate & normalize incoming data
    loaded = CreateEventSchema().load(raw_payload)

    # 2) Creating a mock user and guests list
    organizer = User(id=2, name="Bob", surname="Jones", email="bob@example.com")
    guests = [
        User(name=f"Name {i}", surname=f"Surname {i}", email=f"email{i}@example.com")
        for i in range(3)
    ]
    event = Event(
        title=loaded["title"],
        location=loaded["location"],
        description=loaded["description"],
        category=loaded["category"],
        datetime=loaded["datetime"],
        organizer=organizer,
        organizer_id=2,
    )
    event.guests = guests

    # 3) DUMP
    dumped = EventSchema().dump(event)

    # 4) ASSERTIONS
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
    }
    with pytest.raises(ValidationError):
        CreateEventSchema().load(bad)



