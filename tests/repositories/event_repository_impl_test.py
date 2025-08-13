import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import scoped_session, sessionmaker, Session
from unittest.mock import MagicMock
from app import create_app
from app.extensions import db as _db
from app.models.event import Event
from app.models.user import User
from app.repositories.event_repository_impl import EventRepositoryImpl
from tests.util.util_test import test_cfg
from app.configuration.config import Config

# ---------- App & DB setup ----------

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


# ---------- Repo & data fixtures ----------

@pytest.fixture
def event_repo():
    # repo methods now take `session` per call; no session in constructor
    return EventRepositoryImpl()


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
    return datetime(2025, 1, 1, 10, 0, 0)


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
    dummy_vector = [0.0] * Config.UNIFIED_VECTOR_DIM
    created_events = []
    for e in event_data:
        event = Event(
            title=e["title"],
            datetime=e["datetime"],
            description=e["description"],
            organizer_id=organizer_user.id,
            location=e["location"],
            category=e["category"],
            embedding=dummy_vector
        )
        saved_event = event_repo.save(event, db_session())
        db_session.commit()
        created_events.append(saved_event)

    return created_events


# ----------------------------------------
# Test: get_all() -> List[Event]
# Verify that all events stored in the database are returned correctly.
# Ensure the returned list matches the expected number of saved events.
# ----------------------------------------

def test_get_all_events(event_repo, events_fixture, db_session):
    fetched = event_repo.get_all(db_session())
    assert len(fetched) == len(events_fixture)

    saved_ids = {e.id for e in events_fixture}
    fetched_ids = {e.id for e in fetched}
    assert saved_ids.issubset(fetched_ids)


def test_get_by_id(event_repo, events_fixture, db_session):
    event = events_fixture[0]
    fetched_event = event_repo.get_by_id(event.id, db_session)
    assert fetched_event == event


def test_get_by_title_existing(event_repo, events_fixture, db_session):
    event = events_fixture[0]
    fetched_event = event_repo.get_by_title(event.title, db_session)
    assert fetched_event is not None
    assert fetched_event.id == event.id
    assert fetched_event.title == event.title

def test_get_by_title_nonexistent(event_repo, db_session):
    fetched_event = event_repo.get_by_title("Nonexistent Event Title", db_session)
    assert fetched_event is None


def test_get_by_organizer_id(event_repo, events_fixture, db_session):
    events = event_repo.get_by_organizer_id(events_fixture[0].organizer_id, db_session)
    assert len(events) == len(events_fixture)

    saved_ids = {e.id for e in events_fixture}
    fetched_ids = {e.id for e in events}
    assert saved_ids.issubset(fetched_ids)


def test_get_by_date(event_repo, events_fixture, now, db_session):
    target_date = (now + timedelta(days=5)).date()
    expected_events = [e for e in events_fixture if e.datetime.date() == target_date]
    fetched_events = event_repo.get_by_date(datetime.combine(target_date, datetime.min.time()), db_session)
    assert len(fetched_events) == len(expected_events)

    for event in fetched_events:
        assert event.datetime.date() == target_date

def test_get_by_date_sorted(event_repo, events_fixture, now, db_session):
    target_date = (now + timedelta(days=5)).date()
    fetched = event_repo.get_by_date(datetime.combine(target_date, datetime.min.time()), db_session)
    times = [e.datetime for e in fetched]
    assert times == sorted(times)


def test_get_by_location(event_repo, events_fixture, db_session):
    target_location = events_fixture[1].location
    expected_events = [e for e in events_fixture if e.location == target_location]
    fetched_events = event_repo.get_by_location(target_location, db_session)
    assert len(fetched_events) == len(expected_events)
    for event in fetched_events:
        assert event.location == target_location


def test_get_by_category(event_repo, events_fixture, db_session):
    target_category = events_fixture[0].category
    expected_events = [e for e in events_fixture if e.category == target_category]
    fetched_events = event_repo.get_by_category(target_category, db_session)
    assert len(fetched_events) == len(expected_events)
    for event in fetched_events:
        assert event.category == target_category


def test_save_event(event_repo, organizer_user, now, db_session):
    dummy_vector = [0.0] * Config.UNIFIED_VECTOR_DIM
    new_event = Event(
        title="New Test Event",
        datetime=now + timedelta(days=2),
        description="Test description",
        organizer_id=organizer_user.id,
        location="Test Location",
        category="Test Category",
        embedding=dummy_vector
    )
    saved = event_repo.save(new_event, db_session)
    db_session.commit()

    assert saved.id is not None
    fetched = event_repo.get_by_id(saved.id, db_session)
    assert fetched == saved


def test_delete_by_id(event_repo, events_fixture, db_session):
    target = events_fixture[0]
    event_repo.delete_by_id(target.id, db_session)
    db_session.commit()
    assert event_repo.get_by_id(target.id, db_session) is None


def test_delete_by_title(event_repo, events_fixture, db_session):
    target = events_fixture[2]
    event_repo.delete_by_title(target.title, db_session)
    db_session.commit()
    assert event_repo.get_by_title(target.title, db_session) is None


def test_exists_by_id(event_repo, events_fixture, db_session):
    target = events_fixture[2]
    assert event_repo.exists_by_id(target.id, db_session) is True
    assert event_repo.exists_by_id(9999, db_session) is False


def test_exists_by_title(event_repo, events_fixture, db_session):
    title = events_fixture[3].title
    assert event_repo.exists_by_title(title, db_session) is True
    assert event_repo.exists_by_title("Unknown Title", db_session) is False


def test_exists_by_location(event_repo, events_fixture, db_session):
    location = events_fixture[3].location
    assert event_repo.exists_by_location(location, db_session) is True
    assert event_repo.exists_by_location("Random Unknown Place", db_session) is False


def test_exists_by_category(event_repo, events_fixture, db_session):
    category = events_fixture[3].category
    assert event_repo.exists_by_category(category, db_session) is True
    assert event_repo.exists_by_category("Nonexistent Category", db_session) is False


def test_exists_by_date(event_repo, events_fixture, now, db_session):
    target_date = datetime.combine(events_fixture[0].datetime.date(), datetime.min.time())
    assert event_repo.exists_by_date(target_date, db_session) is True
    assert event_repo.exists_by_date(datetime(1999, 1, 1), db_session) is False



#----------------------------------------
#    Testing the search_by_embedding method.
#---------------------------------------

class _ScalarResultStub:
    def __init__(self, items):
        self._items = items
    def all(self):
        return self._items

class _ExecuteResultStub:
    def __init__(self, items):
        self._items = items
    def scalars(self):
        return _ScalarResultStub(self._items)

def test_search_by_embedding_unit_mock_with_embeddings():
    # Create a mock session
    fake_session = MagicMock(spec=Session)

    D = Config.UNIFIED_VECTOR_DIM
    e1 = Event(id=1, title="closest"); e1.embedding = [1.0] + [0.0] * (D - 1)
    e2 = Event(id=2, title="second");  e2.embedding = [2.0] + [0.0] * (D - 1)

    # First execute: SET LOCAL probes → ignored
    # Second execute: SELECT query → returns events
    fake_session.execute.side_effect = [
        MagicMock(),
        _ExecuteResultStub([e1, e2]),
    ]

    repo = EventRepositoryImpl()

    q = [0.9] + [0.0] * (D - 1)
    out = repo.search_by_embedding(q, k=2, probes=10, session=fake_session)

    # Assertions
    assert isinstance(out, list)
    assert [e.title for e in out] == ["closest", "second"]
    assert len(out[0].embedding) == D and out[0].embedding[0] == 1.0
    assert len(out[1].embedding) == D and out[1].embedding[0] == 2.0

    # Verify calls
    set_call, select_call = fake_session.execute.call_args_list
    assert "SET LOCAL ivfflat.probes" in str(set_call.args[0])  # first call text
    params = select_call.args[1]  # second positional arg is dict {"q": vec, "k": 2}
    assert params["k"] == 2
