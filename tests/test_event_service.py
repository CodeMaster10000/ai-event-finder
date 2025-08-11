"""
Unit tests for the EventServiceImpl class.

These tests mock the EventRepository to verify business logic in isolation,
including proper exception handling and delegation of operations.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime
from sqlalchemy.orm import Session
from unittest.mock import ANY
from app.models.event import Event
from app.models.user import User
from app.services.event_service_impl import EventServiceImpl
from app.error_handler.exceptions import (
    EventNotFoundException,
    EventAlreadyExistsException,
    EventSaveException,
    EventDeleteException,
    UserNotFoundException
)


# -------------------------------
# Fixtures
# -------------------------------

@pytest.fixture
def fake_session():
    s = MagicMock(spec=Session)
    s.commit = MagicMock()
    s.rollback = MagicMock()

    class _NoAutoflush:
        def __enter__(self): return None
        def __exit__(self, *a): return False
    s.no_autoflush = _NoAutoflush()
    return s

@pytest.fixture
def patch_db_session(fake_session, monkeypatch):
    # Set db.session to a NON-callable fake Session object.
    from app import extensions as _ext
    monkeypatch.setattr(_ext.db, "session", fake_session)
    return fake_session

@pytest.fixture
def mock_event_repo():
    return MagicMock()

@pytest.fixture
def mock_user_repo():
    return MagicMock()

@pytest.fixture
def event_service(mock_event_repo, mock_user_repo):
    svc = EventServiceImpl(event_repository=mock_event_repo, user_repository=mock_user_repo)
    # inject embedding_service used by create()/update()
    svc.embedding_service = MagicMock()
    svc.embedding_service.create_embedding.return_value = [0.1, 0.2, 0.3]
    return svc


# -------------------------------
# Tests
# -------------------------------

def test_get_by_title_success(event_service, mock_event_repo, patch_db_session):
    organizer = User(id=1, name="Name", surname="Surname", email="email@example.com", password="secret")
    event = Event(id=1, title="Event 1", organizer=organizer, datetime=datetime.now(),
                  description="Event description", organizer_id=organizer.id,
                  location="Location 1", category="category")
    mock_event_repo.get_by_title.return_value = event

    result = event_service.get_by_title("Event 1")

    mock_event_repo.get_by_title.assert_called_once_with("Event 1", patch_db_session)
    assert result == event


def test_get_by_title_raises_if_not_found(event_service, mock_event_repo, patch_db_session):
    mock_event_repo.get_by_title.return_value = None

    with pytest.raises(EventNotFoundException, match="Event 1"):
        event_service.get_by_title("Event 1")

    mock_event_repo.get_by_title.assert_called_once_with("Event 1", patch_db_session)


def test_get_by_category(event_service, mock_event_repo, patch_db_session):
    events = [Event(id=1, title="E", organizer_id=1, datetime=datetime.now(),
                    description="d", location="L", category="category")]
    mock_event_repo.get_by_category.return_value = events

    result = event_service.get_by_category("category")

    mock_event_repo.get_by_category.assert_called_once_with("category", patch_db_session)
    assert result == events


def test_get_by_location(event_service, mock_event_repo, patch_db_session):
    events = [Event(id=1, title="E", organizer_id=1, datetime=datetime.now(),
                    description="d", location="Location 1", category="category")]
    mock_event_repo.get_by_location.return_value = events

    result = event_service.get_by_location("Location 1")

    mock_event_repo.get_by_location.assert_called_once_with("Location 1", patch_db_session)
    assert result == events


def test_get_by_date(event_service, mock_event_repo, patch_db_session):
    dt = datetime.now()
    events = [Event(id=1, title="E", organizer_id=1, datetime=dt,
                    description="d", location="L", category="C")]
    mock_event_repo.get_by_date.return_value = events

    result = event_service.get_by_date(dt)

    mock_event_repo.get_by_date.assert_called_once_with(dt, patch_db_session)
    assert result == events


def test_get_by_organizer_success(event_service, mock_user_repo, mock_event_repo, patch_db_session):
    organizer = User(id=1, name="Name", surname="Surname", email="email@example.com", password="secret")
    event = Event(id=1, title="Event 1", organizer=organizer, datetime=datetime.now(),
                  description="Event description", organizer_id=organizer.id,
                  location="Location 1", category="category")

    mock_user_repo.get_by_email.return_value = organizer
    mock_event_repo.get_by_organizer_id.return_value = [event]

    result = event_service.get_by_organizer("email@example.com")

    mock_user_repo.get_by_email.assert_called_once_with("email@example.com", patch_db_session)
    mock_event_repo.get_by_organizer_id.assert_called_once_with(organizer.id, patch_db_session)
    assert result == [event]


def test_get_by_organizer_raises_if_user_not_found(event_service, mock_user_repo, patch_db_session):
    mock_user_repo.get_by_email.return_value = None

    with pytest.raises(UserNotFoundException, match="No user found with email email@example.com"):
        event_service.get_by_organizer("email@example.com")

    mock_user_repo.get_by_email.assert_called_once_with("email@example.com", patch_db_session)


def test_get_all(event_service, mock_event_repo, patch_db_session):
    events = [
        Event(id=1, title="Event 1", organizer_id=1, datetime=datetime.now(), description="d", location="L1", category="C"),
        Event(id=2, title="Event 2", organizer_id=2, datetime=datetime.now(), description="d", location="L2", category="C"),
    ]
    mock_event_repo.get_all.return_value = events

    result = event_service.get_all()

    mock_event_repo.get_all.assert_called_once_with(patch_db_session)
    assert result == events

def test_create_event(event_service, mock_event_repo, mock_user_repo, patch_db_session):
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

    def _save(e, session):
        e.id = 42
        return e
    mock_event_repo.save.side_effect = _save

    result = event_service.create(payload)

    # first duplicate check uses direct db.session (your patched one)
    c0_args, _ = mock_event_repo.get_by_title.call_args_list[0]
    assert c0_args == ('Event 1', patch_db_session)
    # TOCTOU recheck uses decorator session -> allow ANY
    c1_args, _ = mock_event_repo.get_by_title.call_args_list[1]
    assert c1_args == ('Event 1', ANY)

    # save happens inside the decorator transaction -> allow ANY session
    mock_event_repo.save.assert_called_once()
    s_args, _ = mock_event_repo.save.call_args
    assert s_args[0].title == 'Event 1'

    assert result.id == 42


def test_create_raises_on_duplicate_title(event_service, mock_event_repo, mock_user_repo, patch_db_session):
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    mock_user_repo.get_by_email.return_value = organizer

    existing = Event(
        title='DupEvent',
        description='desc',
        datetime=datetime.now(),
        location='loc',
        category='cat',
        organizer_id=organizer.id
    )
    mock_event_repo.get_by_title.return_value = existing

    payload = {
        'title':           'DupEvent',
        'description':     'desc',
        'datetime':        datetime.now(),
        'location':        'loc',
        'category':        'cat',
        'organizer_email': organizer.email
    }

    with pytest.raises(EventAlreadyExistsException) as exc:
        event_service.create(payload)
    assert 'DupEvent' in str(exc.value)

    mock_event_repo.get_by_title.assert_called_once_with('DupEvent', patch_db_session)

def test_delete_by_title_success(event_service, mock_event_repo, patch_db_session):
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    event = Event(id=1, title='Event 1', organizer=organizer, datetime=datetime.now(),
                  description='Event description', organizer_id=organizer.id,
                  location='Location 1', category='category')
    mock_event_repo.get_by_title.return_value = event

    # sanity (non-decorated call)
    result = event_service.get_by_title("Event 1")
    assert result == event
    mock_event_repo.get_by_title.assert_any_call("Event 1", patch_db_session)

    # decorated call uses its own session -> ANY
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

    # decorated calls -> ANY
    mock_event_repo.get_by_title.assert_called_with("Event 1", ANY)
    mock_event_repo.delete_by_title.assert_called_once_with("Event 1", ANY)


def test_create_wraps_repository_errors(event_service, mock_event_repo, mock_user_repo, patch_db_session):
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    mock_user_repo.get_by_email.return_value = organizer
    mock_event_repo.get_by_title.side_effect = [None, None]
    mock_event_repo.save.side_effect = RuntimeError("db down")

    payload = {
        'title':           'CrashEvent',
        'description':     'desc',
        'datetime':        datetime.now(),
        'location':        'loc',
        'category':        'cat',
        'organizer_email': organizer.email
    }

    with pytest.raises(EventSaveException) as exc:
        event_service.create(payload)
    assert str(exc.value) == 'Unable to save event due to an internal error.'

def test_update_success(event_service, mock_event_repo, patch_db_session):
    """update should call save() on an existing event when no conflicts."""
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    event = Event(id=1, title='Event 1', organizer=organizer, datetime=datetime.now(),
                  description='Event description', organizer_id=organizer.id,
                  location='Location 1', category='category')

    mock_event_repo.get_by_id.return_value = event
    # pre-check uses direct session, TOCTOU recheck uses decorator session
    mock_event_repo.get_by_title.side_effect = [event, None]

    def _save(e, session): return e
    mock_event_repo.save.side_effect = _save

    result = event_service.update(event)

    mock_event_repo.get_by_id.assert_called_once_with(event.id, patch_db_session)

    a0, _ = mock_event_repo.get_by_title.call_args_list[0]
    a1, _ = mock_event_repo.get_by_title.call_args_list[1]
    assert a0 == (event.title, patch_db_session)  # direct
    assert a1 == (event.title, ANY)               # decorator

    # save happens inside decorator -> ANY
    mock_event_repo.save.assert_called_once()
    s_args, _ = mock_event_repo.save.call_args
    assert s_args[0] is event

    assert result is event



def test_update_raises_not_found(event_service, mock_event_repo, patch_db_session):
    mock_event_repo.get_by_id.return_value = None

    with pytest.raises(EventNotFoundException):
        event_service.update(Event(id=1, title='Event 1', organizer_id=1,
                                   datetime=datetime.now(), description='Event description',
                                   location='Location 1', category='category'))


def test_update_raises_duplicate_title(event_service, mock_event_repo, patch_db_session):
    """update should raise EventAlreadyExists when another event already has that title."""
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    original = Event(id=1, title='Event 1', organizer=organizer, datetime=datetime.now(),
                     description='Event description', organizer_id=organizer.id,
                     location='Location 1', category='category')

    conflict = Event(id=2, title='Event 1', organizer=organizer, datetime=datetime.now(),
                     description='Event description', organizer_id=organizer.id,
                     location='Location 2', category='category')

    mock_event_repo.get_by_id.return_value = original
    # Pre-check already finds conflicting OTHER event → raises before TOCTOU
    mock_event_repo.get_by_title.return_value = conflict

    with pytest.raises(EventAlreadyExistsException):
        event_service.update(original)


def test_update_wraps_save_errors(event_service, mock_event_repo, patch_db_session):
    """update should catch repo.save exceptions and re-raise EventSaveException."""
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    event = Event(id=1, title='Event 1', organizer=organizer, datetime=datetime.now(),
                  description='Event description', organizer_id=organizer.id,
                  location='Location 1', category='category')
    mock_event_repo.get_by_id.return_value = event
    # allow through conflict checks, then fail on save
    mock_event_repo.get_by_title.side_effect = [event, None]
    mock_event_repo.save.side_effect = ValueError("oops")

    with pytest.raises(EventSaveException) as ei:
        event_service.update(event)

    assert isinstance(ei.value.original_exception, ValueError)
