import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import scoped_session, sessionmaker

from app import create_app
from app.extensions import db as _db
from app.models.event import Event
from app.models.user import User
from app.repositories.event_repository_impl import EventRepositoryImpl
from tests.util.test_util import test_cfg


# App fixture
@pytest.fixture
def app():
    app = create_app(test_cfg)
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


# DB session fixture
@pytest.fixture
def db_session(app):
    connection = _db.engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)

    yield session

    session.remove()
    transaction.rollback()
    connection.close()


# Event repository fixture
@pytest.fixture
def event_repo(db_session):
    return EventRepositoryImpl(db_session())


# Organizer (user) fixture
@pytest.fixture
def organizer_user(db_session):
    user = User(
        name="Test",
        surname="User",
        email="organizer@example.com",
        password="dummy-hash"
    )
    db_session.add(user)
    db_session.commit()
    return user


# Datetime timestamp now fixture
@pytest.fixture
def now():
    return datetime(2025,1,1,10,0,0)


# Events fixture
@pytest.fixture
def events_fixture(event_repo, db_session, organizer_user, now):
    event_data = [
        {
            "title": "Tech Conference 2025",
            "datetime": now + timedelta(days=5, hours=14),
            "description": "Annual technology conference featuring speakers from major tech companies.",
            "location": "Tech Arena, Berlin",
            "category": "Technology",
        },
        {
            "title": "Jazz Night Live",
            "datetime": now + timedelta(days=10, hours=20),
            "description": "An evening of smooth jazz with top European artists.",
            "location": "Blue Note Club, Paris",
            "category": "Music",
        },
        {
            "title": "Startup Pitch Day",
            "datetime": now + timedelta(days=7, hours=9, minutes=30),
            "description": "Early-stage startups present their ideas to investors and incubators.",
            "location": "Startup Hub, Amsterdam",
            "category": "Business",
        },
        {
            "title": "Python Bootcamp",
            "datetime": now + timedelta(days=15, hours=8),
            "description": "A full-day Python training for beginners and intermediate developers.",
            "location": "CodeBase, London",
            "category": "Education",
        },
        {
            "title": "Outdoor Film Screening",
            "datetime": now + timedelta(days=5, hours=21),
            "description": "A community film night screening classic movies under the stars.",
            "location": "Central Park, New York",
            "category": "Entertainment",
        }
    ]

    created_events = []
    for e in event_data:
        event = Event(
            title=e["title"],
            datetime=e["datetime"],
            description=e["description"],
            organizer_id=organizer_user.id,
            location=e["location"],
            category=e["category"]
        )
        saved_event = event_repo.save(event)
        created_events.append(saved_event)

    event_repo.session.commit()
    return created_events


# ----------------------------------------
# Test: get_all() -> List[Event]
# Verify that all events stored in the database are returned correctly.
# Ensure the returned list matches the expected number of saved events.
# ----------------------------------------

def test_get_all_events(event_repo, events_fixture):
    fetched = event_repo.get_all()
    assert len(fetched) == len(events_fixture)

    saved_ids = {e.id for e in events_fixture}
    fetched_ids = {e.id for e in fetched}
    assert saved_ids.issubset(fetched_ids)


# ----------------------------------------
# Test: get_by_id(event_id: int) -> Optional[Event]
# Verify that an event can be retrieved by its ID.
# Ensure that it returns None if the ID does not exist.
# ----------------------------------------

def test_get_by_id(event_repo, events_fixture):
    event = events_fixture[0]
    fetched_event = event_repo.get_by_id(event.id)
    assert fetched_event == event


# ----------------------------------------
# Test: get_by_title(title: str) -> Optional[Event]
# Verify that an event can be retrieved by its title.
# Ensure that it returns None for a nonexistent title.
# ----------------------------------------

def test_get_by_title_existing(event_repo, events_fixture):
    event = events_fixture[0]
    fetched_event = event_repo.get_by_title(event.title)
    assert fetched_event is not None
    assert fetched_event.id == event.id
    assert fetched_event.title == event.title


def test_get_by_title_nonexistent(event_repo, events_fixture):
    fetched_event = event_repo.get_by_title("Nonexistent Event Title")
    assert fetched_event is None


# ----------------------------------------
# Test: get_by_organizer_id(organizer_id: int) -> List[Event]
# Ensure that all events tied to a specific organizer ID are retrieved.
# ----------------------------------------

def test_get_by_organizer_id(event_repo, events_fixture):
    events = event_repo.get_by_organizer_id(events_fixture[0].organizer_id)
    assert len(events) == len(events_fixture)

    saved_ids = {e.id for e in events_fixture}
    fetched_ids = {e.id for e in events}
    assert saved_ids.issubset(fetched_ids)


# ----------------------------------------
# Test: get_by_date(date: datetime) -> List[Event]
# Ensure that all events occurring on the given date (ignoring time) are retrieved.
# Confirm they are sorted in ascending order by time (datetime).
# ----------------------------------------

def test_get_by_date(event_repo, events_fixture, now):
    target_date = (now + timedelta(days=5)).date()
    expected_events = [e for e in events_fixture if e.datetime.date() == target_date]
    fetched_events = event_repo.get_by_date(datetime.combine(target_date, datetime.min.time()))
    assert len(fetched_events) == len(expected_events)

    for event in fetched_events:
        assert event.datetime.date() == target_date

def test_get_by_date_sorted(event_repo, events_fixture, now):
    target_date = (now + timedelta(days=5)).date()
    fetched = event_repo.get_by_date(datetime.combine(target_date, datetime.min.time()))
    times = [e.datetime for e in fetched]
    assert times == sorted(times)


# ----------------------------------------
# Test: get_by_location(location: str) -> List[Event]
# Ensure that events at a given location are retrieved.
# ----------------------------------------

def test_get_by_location(event_repo, events_fixture):
    target_location = events_fixture[1].location
    expected_events = [e for e in events_fixture if e.location == target_location]
    fetched_events = event_repo.get_by_location(target_location)
    assert len(fetched_events) == len(expected_events)
    for event in fetched_events:
        assert event.location == target_location


# ----------------------------------------
# Test: get_by_category(category: str) -> List[Event]
# Ensure that events belonging to a certain category are retrieved.
# ----------------------------------------

def test_get_by_category(event_repo, events_fixture):
    target_category = events_fixture[0].category
    expected_events = [e for e in events_fixture if e.category == target_category]
    fetched_events = event_repo.get_by_category(target_category)
    assert len(fetched_events) == len(expected_events)
    for event in fetched_events:
        assert event.category == target_category


# ----------------------------------------
# Test: save(event: Event) -> Event
# Confirm that an event is successfully saved to the database.
# Check that a valid ID is assigned and data is persisted.
# ----------------------------------------

def test_save_event(event_repo, organizer_user, now):
    new_event = Event(
        title="New Test Event",
        datetime=now + timedelta(days=2),
        description="Test description",
        organizer_id=organizer_user.id,
        location="Test Location",
        category="Test Category"
    )
    saved = event_repo.save(new_event)
    event_repo.session.commit()

    assert saved.id is not None
    fetched = event_repo.get_by_id(saved.id)
    assert fetched == saved


# ----------------------------------------
# Test: delete_by_id(event_id: int) -> None
# Test that an event is deleted if it exists by its ID.
# Confirm that the event is no longer retrievable after deletion.
# ----------------------------------------

def test_delete_by_id(event_repo, events_fixture):
    target = events_fixture[0]
    event_repo.delete_by_id(target.id)

    assert event_repo.get_by_id(target.id) is None


# ----------------------------------------
# Test: delete_by_title(title: str) -> None
# Test that an event is deleted by its title.
# Confirm that it no longer exists after deletion.
# ----------------------------------------

def test_delete_by_title(event_repo, events_fixture):
    target = events_fixture[2]
    event_repo.delete_by_title(target.title)

    assert event_repo.get_by_title(target.title) is None


# ----------------------------------------
# Test: exists_by_id(event_id: int) -> bool
# Confirm that True is returned if the event exists by ID.
# Ensure False is returned for a nonexistent ID.
# ----------------------------------------

def test_exists_by_id(event_repo, events_fixture):
    target = events_fixture[2]
    assert event_repo.exists_by_id(target.id) is True
    assert event_repo.exists_by_id(9999) is False


# ----------------------------------------
# Test: exists_by_title(title: str) -> bool
# Confirm that existence check works properly for a title.
# ----------------------------------------

def test_exists_by_title(event_repo, events_fixture):
    title = events_fixture[3].title
    assert event_repo.exists_by_title(title) is True
    assert event_repo.exists_by_title("Unknown Title") is False


# ----------------------------------------
# Test: exists_by_location(location: str) -> bool
# Confirm that existence check works properly for location.
# ----------------------------------------

def test_exists_by_location(event_repo, events_fixture):
    location = events_fixture[3].location
    assert event_repo.exists_by_location(location) is True
    assert event_repo.exists_by_location("Random Unknown Place") is False


# ----------------------------------------
# Test: exists_by_category(category: str) -> bool
# Confirm that existence check works properly for category.
# ----------------------------------------

def test_exists_by_category(event_repo, events_fixture):
    category = events_fixture[3].category
    assert event_repo.exists_by_category(category) is True
    assert event_repo.exists_by_category("Nonexistent Category") is False


# ----------------------------------------
# Test: exists_by_date(date: datetime) -> bool
# Confirm that existence check works properly for date (ignores time).
# ----------------------------------------

def test_exists_by_date(event_repo, events_fixture, now):
    target_date = datetime.combine(events_fixture[0].datetime.date(), datetime.min.time())

    assert event_repo.exists_by_date(target_date) is True
    assert event_repo.exists_by_date(datetime(1999,1,1)) is False