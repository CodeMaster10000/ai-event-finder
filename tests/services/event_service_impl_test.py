"""
Unit tests for the EventServiceImpl class.

These tests mock the repositories and embedding service to verify business logic
in isolation, including proper exception handling and delegation of operations.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, ANY
from datetime import datetime

from flask import Flask
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.user import User
from app.services.event_service_impl import EventServiceImpl
from app.error_handler.exceptions import (
    EventNotFoundException,
    EventDeleteException,
    UserNotFoundException,
)
from app.extensions import db


# -------------------------------
# Fixtures
# -------------------------------

@pytest.fixture(scope="session")
def app():
    """
    Minimal Flask app for unit tests.
    In-memory SQLite, no create_app().
    """
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)

    with app.app_context():
        # Import models so create_all() knows what to create
        from app.models.user import User   # noqa: F401
        from app.models.event import Event # noqa: F401

        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _make_fake_session() -> MagicMock:
    """Build a Session-like MagicMock that works with the transactional util."""
    s = MagicMock(spec=Session)
    s.commit = MagicMock()
    s.rollback = MagicMock()
    s.flush = MagicMock()
    s.close = MagicMock()
    s.remove = MagicMock()
    s.in_transaction = MagicMock(return_value=False)

    class _NoAutoflush:
        def __enter__(self): return None
        def __exit__(self, *a): return False

    s.no_autoflush = _NoAutoflush()
    return s


@pytest.fixture
def patch_db_session(monkeypatch):
    """
    Make db.session a **callable** factory (db.session()) that returns the same
    fake session for the whole test. This matches the service's transactional use.
    """
    fake_session = _make_fake_session()
    session_factory = MagicMock(name="session_factory", return_value=fake_session)

    # Patch the *attribute* on the extensions module so anyone importing from there gets it.
    from app import extensions as _ext
    monkeypatch.setattr(_ext.db, "session", session_factory)
    # Also patch the imported symbol in this module (defensive; some code imports `db` directly)
    monkeypatch.setattr(db, "session", session_factory)

    return fake_session


@pytest.fixture
def mock_event_repo():
    return MagicMock()


@pytest.fixture
def mock_user_repo():
    return MagicMock()


@pytest.fixture
def mock_embedding_service():
    m = MagicMock()
    # embedding service is awaited by the async service methods
    m.create_embedding = AsyncMock()
    return m


@pytest.fixture
def event_service(mock_event_repo, mock_user_repo, mock_embedding_service):
    return EventServiceImpl(
        event_repository=mock_event_repo,
        user_repository=mock_user_repo,
        embedding_service=mock_embedding_service,
    )


# -------------------------------
# Sync GET / DELETE tests
# -------------------------------

def test_get_by_title_success(event_service, mock_event_repo, patch_db_session):
    organizer = User(id=1, name="Name", surname="Surname", email="email@example.com", password="secret")
    event = Event(id=1, title="Event 1", organizer=organizer, datetime=datetime.now(),
                  description="Event description", organizer_id=organizer.id,
                  location="Location 1", category="category")
    mock_event_repo.get_by_title.return_value = event

    result = event_service.get_by_title("Event 1")

    mock_event_repo.get_by_title.assert_called_once_with("Event 1", ANY)
    assert result == event


def test_get_by_title_raises_if_not_found(event_service, mock_event_repo, patch_db_session):
    mock_event_repo.get_by_title.return_value = None

    with pytest.raises(EventNotFoundException, match="Event 1"):
        event_service.get_by_title("Event 1")

    mock_event_repo.get_by_title.assert_called_once_with("Event 1", ANY)


def test_get_by_category(event_service, mock_event_repo, patch_db_session):
    events = [Event(id=1, title="E", organizer_id=1, datetime=datetime.now(),
                    description="d", location="L", category="category")]
    mock_event_repo.get_by_category.return_value = events

    result = event_service.get_by_category("category")

    mock_event_repo.get_by_category.assert_called_once_with("category", ANY)
    assert result == events


def test_get_by_location(event_service, mock_event_repo, patch_db_session):
    events = [Event(id=1, title="E", organizer_id=1, datetime=datetime.now(),
                    description="d", location="Location 1", category="category")]
    mock_event_repo.get_by_location.return_value = events

    result = event_service.get_by_location("Location 1")

    mock_event_repo.get_by_location.assert_called_once_with("Location 1", ANY)
    assert result == events


def test_get_by_date(event_service, mock_event_repo, patch_db_session):
    dt = datetime.now()
    events = [Event(id=1, title="E", organizer_id=1, datetime=dt,
                    description="d", location="L", category="C")]
    mock_event_repo.get_by_date.return_value = events

    result = event_service.get_by_date(dt)

    mock_event_repo.get_by_date.assert_called_once_with(dt, ANY)
    assert result == events


def test_get_by_organizer_success(event_service, mock_user_repo, mock_event_repo, patch_db_session):
    organizer = User(id=1, name="Name", surname="Surname", email="email@example.com", password="secret")
    event = Event(id=1, title="Event 1", organizer=organizer, datetime=datetime.now(),
                  description="Event description", organizer_id=organizer.id,
                  location="Location 1", category="category")

    mock_user_repo.get_by_email.return_value = organizer
    mock_event_repo.get_by_organizer_id.return_value = [event]

    result = event_service.get_by_organizer("email@example.com")

    mock_user_repo.get_by_email.assert_called_once_with("email@example.com", ANY)
    mock_event_repo.get_by_organizer_id.assert_called_once_with(organizer.id, ANY)
    assert result == [event]


def test_get_by_organizer_raises_if_user_not_found(event_service, mock_user_repo, patch_db_session):
    mock_user_repo.get_by_email.return_value = None

    with pytest.raises(UserNotFoundException, match="No user found with email email@example.com"):
        event_service.get_by_organizer("email@example.com")

    mock_user_repo.get_by_email.assert_called_once_with("email@example.com", ANY)


def test_get_all(event_service, mock_event_repo, patch_db_session):
    organizer1 = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    event1 = Event(id=1,
                   title='Event 1',
                   organizer=organizer1,
                   datetime=datetime.now(),
                   description='Event description',
                   organizer_id=organizer1.id,
                   location='Location 1',
                   category='category')

    organizer2 = User(id=2, name='Name', surname='Surname', email='email123', password='secret')
    event2 = Event(id=2,
                   title='Event 2',
                   organizer=organizer2,
                   datetime=datetime.now(),
                   description='Event description',
                   organizer_id=organizer2.id,
                   location='Location 2',
                   category='category')

    events = [event1, event2]
    mock_event_repo.get_all.return_value = events

    result = event_service.get_all()

    mock_event_repo.get_all.assert_called_once_with(ANY)
    assert result == events


def test_delete_by_title_success(event_service, mock_event_repo, patch_db_session):
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    event = Event(id=1, title='Event 1', organizer=organizer, datetime=datetime.now(),
                  description='Event description', organizer_id=organizer.id,
                  location='Location 1', category='category')
    mock_event_repo.get_by_title.return_value = event

    # sanity (non-decorated direct read or decorated; don't assert session identity)
    result = event_service.get_by_title("Event 1")
    assert result == event
    mock_event_repo.get_by_title.assert_any_call("Event 1", ANY)

    # decorated call uses its own session
    event_service.delete_by_title("Event 1")
    mock_event_repo.delete_by_title.assert_called_once_with("Event 1", ANY)


def test_delete_by_title_raises_if_not_found(event_service, mock_event_repo, patch_db_session):
    mock_event_repo.get_by_title.return_value = None

    with pytest.raises(EventNotFoundException, match="Event 1"):
        event_service.delete_by_title("Event 1")


def test_delete_by_title_wraps_repository_errors(event_service, mock_event_repo, patch_db_session):
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    event = Event(id=1, title='Event 1', organizer=organizer, datetime=datetime.now(),
                  description='Event description', organizer_id=organizer.id,
                  location='Location 1', category='category')

    mock_event_repo.get_by_title.return_value = event
    mock_event_repo.delete_by_title.side_effect = RuntimeError("db down")

    with pytest.raises(EventDeleteException):
        event_service.delete_by_title("Event 1")

    mock_event_repo.get_by_title.assert_called_with("Event 1", ANY)
    mock_event_repo.delete_by_title.assert_called_once_with("Event 1", ANY)


# -------------------------------
# ASYNC create() tests
# -------------------------------

@pytest.mark.asyncio
async def test_create_event(event_service, mock_event_repo, mock_user_repo, mock_embedding_service, patch_db_session):
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    mock_user_repo.get_by_email.return_value = organizer
    # create(): pre-check duplicate, then _persist TOCTOU recheck => two calls
    mock_event_repo.get_by_title.side_effect = [None, None]

    payload = {
        'title':           'Event 1',
        'description':     'Event description',
        'datetime':        datetime.now(),
        'location':        'Location 1',
        'category':        'category',
        'organizer_email': organizer.email
    }

    # embedding result
    mock_embedding_service.create_embedding.return_value = [0.1, 0.2, 0.3]

    # Let save() return the SAME object it was given (and set id)
    def _save(e, session):
        e.id = 42
        return e
    mock_event_repo.save.side_effect = _save

    result = await event_service.create(payload)

    # Two duplicate checks happened with ANY session
    assert [args[0] for args, _ in mock_event_repo.get_by_title.call_args_list] == ['Event 1', 'Event 1']

    # save happens inside the decorator transaction -> ANY session
    mock_event_repo.save.assert_called_once()