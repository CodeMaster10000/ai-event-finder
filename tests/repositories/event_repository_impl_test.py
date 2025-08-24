# tests/repositories/event_repository_impl_test.py

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import scoped_session, sessionmaker

from app import create_app
from app.extensions import db as _db
from app.models.event import Event
from app.models.user import User
from app.repositories.event_repository_impl import EventRepositoryImpl
from app.configuration.config import Config
from tests.util.util_test import test_cfg


@pytest.fixture(scope="session")
def app():
    app = create_app(test_cfg)
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield app
        _db.session.remove()

@pytest.fixture(autouse=True)
def clean_db(app):
    with app.app_context():
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()

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

# ---------- Repo + helper fixtures ----------

@pytest.fixture
def event_repo():
    return EventRepositoryImpl()

@pytest.fixture
def organizer_user(db_session):
    u = User(
        name="Test",
        surname="User",
        email="organizer@example.com",
        password="dummy-hash",
    )
    db_session().add(u)
    db_session.commit()
    return u

@pytest.fixture
def now():
    return datetime(2025, 1, 1, 10, 0, 0)

@pytest.fixture
def events_fixture(event_repo, db_session, organizer_user, now):
    data = [
        {"title": "Tech Conference 2025", "datetime": now + timedelta(days=5, hours=14),
         "description": "Annual technology conference featuring speakers from major tech companies.",
         "location": "Tech Arena, Berlin", "category": "Technology"},
        {"title": "Jazz Night Live", "datetime": now + timedelta(days=10, hours=20),
         "description": "An evening of smooth jazz with top European artists.",
         "location": "Blue Note Club, Paris", "category": "Music"},
        {"title": "Startup Pitch Day", "datetime": now + timedelta(days=7, hours=9, minutes=30),
         "description": "Early-stage startups present their ideas to investors and incubators.",
         "location": "Startup Hub, Amsterdam", "category": "Business"},
        {"title": "Python Bootcamp", "datetime": now + timedelta(days=15, hours=8),
         "description": "A full-day Python training for beginners and intermediate developers.",
         "location": "CodeBase, London", "category": "Education"},
        {"title": "Outdoor Film Screening", "datetime": now + timedelta(days=5, hours=21),
         "description": "A community film night screening classic movies under the stars.",
         "location": "Central Park, New York", "category": "Entertainment"},
    ]
    dummy_vec = [0.0] * Config.UNIFIED_VECTOR_DIM
    out = []
    for e in data:
        ev = Event(
            title=e["title"],
            datetime=e["datetime"],
            description=e["description"],
            organizer_id=organizer_user.id,
            location=e["location"],
            category=e["category"],
            embedding=dummy_vec,
        )
        saved = event_repo.save(ev, db_session())  # save with session()
        db_session.commit()
        out.append(saved)
    return out


# ---------- Tests ----------

def test_get_all_events(event_repo, events_fixture, db_session):
    fetched = event_repo.get_all(db_session())  # session()
    assert len(fetched) == len(events_fixture)
    assert {e.id for e in events_fixture}.issubset({e.id for e in fetched})

def test_get_by_id(event_repo, events_fixture, db_session):
    event = events_fixture[0]
    fetched = event_repo.get_by_id(event.id, db_session)  # session object
    assert fetched == event

def test_get_by_title_existing(event_repo, events_fixture, db_session):
    event = events_fixture[0]
    fetched = event_repo.get_by_title(event.title, db_session)  # session object
    assert fetched is not None and fetched.id == event.id and fetched.title == event.title

def test_get_by_title_nonexistent(event_repo, db_session):
    assert event_repo.get_by_title("Nonexistent Event Title", db_session) is None

def test_get_by_organizer_id(event_repo, events_fixture, db_session):
    events = event_repo.get_by_organizer_id(events_fixture[0].organizer_id, db_session)  # object
    assert len(events) == len(events_fixture)
    assert {e.id for e in events_fixture}.issubset({e.id for e in events})

def test_get_by_date(event_repo, events_fixture, now, db_session):
    target_date = (now + timedelta(days=5)).date()
    fetched = event_repo.get_by_date(datetime.combine(target_date, datetime.min.time()), db_session)  # object
    assert all(e.datetime.date() == target_date for e in fetched)

def test_get_by_date_sorted(event_repo, events_fixture, now, db_session):
    target_date = (now + timedelta(days=5)).date()
    fetched = event_repo.get_by_date(datetime.combine(target_date, datetime.min.time()), db_session)  # object
    times = [e.datetime for e in fetched]
    assert times == sorted(times)

def test_get_by_location(event_repo, events_fixture, db_session):
    loc = events_fixture[1].location
    fetched = event_repo.get_by_location(loc, db_session)  # object
    assert all(e.location == loc for e in fetched)

def test_get_by_category(event_repo, events_fixture, db_session):
    cat = events_fixture[0].category
    fetched = event_repo.get_by_category(cat, db_session)  # object
    assert all(e.category == cat for e in fetched)

def test_save_event(event_repo, organizer_user, now, db_session):
    dummy_vec = [0.0] * Config.UNIFIED_VECTOR_DIM
    ev = Event(
        title="New Test Event",
        datetime=now + timedelta(days=2),
        description="Test description",
        organizer_id=organizer_user.id,
        location="Test Location",
        category="Test Category",
        embedding=dummy_vec,
    )
    saved = event_repo.save(ev, db_session())  # save with session()
    db_session.commit()
    assert event_repo.get_by_id(saved.id, db_session) == saved  # query with session object

def test_delete_by_id(event_repo, events_fixture, db_session):
    target = events_fixture[0]
    event_repo.delete_by_id(target.id, db_session)  # object
    db_session.commit()
    assert event_repo.get_by_id(target.id, db_session) is None

def test_delete_by_title(event_repo, events_fixture, db_session):
    target = events_fixture[2]
    event_repo.delete_by_title(target.title, db_session)  # object
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

def test_exists_by_date(event_repo, events_fixture, db_session):
    target_date = datetime.combine(events_fixture[0].datetime.date(), datetime.min.time())
    assert event_repo.exists_by_date(target_date, db_session) is True
    assert event_repo.exists_by_date(datetime(1999, 1, 1), db_session) is False
