"""
Unit tests for the EventServiceImpl class.

These tests mock the EventRepository to verify business logic in isolation,
including proper exception handling and delegation of operations.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime
from app.models.event import Event
from app.models.user import User
from app.services.event_service_impl import EventServiceImpl
from app.error_handler.exceptions import (
    EventNotFoundException,
    EventAlreadyExistsException,
    EventSaveException,
    EventDeleteException,
    UserNotFoundException)


@pytest.fixture
def mock_event_repo():
    return MagicMock()

@pytest.fixture
def mock_user_repo():
    return MagicMock()

@pytest.fixture
def event_service(mock_event_repo, mock_user_repo):
    return EventServiceImpl(event_repository=mock_event_repo, user_repository=mock_user_repo)


def test_get_by_title_success(event_service, mock_event_repo):
    organizer = User(id=1, name="Name", surname="Surname", email="email@example.com", password="secret")
    event = Event(id=1,
                  title="Event 1",
                  organizer=organizer,
                  datetime=datetime.now(),
                  description="Event description",
                  organizer_id=organizer.id,
                  location="Location 1",
                  category="category")

    mock_event_repo.get_by_title.return_value = event

    result = event_service.get_by_title("Event 1")

    mock_event_repo.get_by_title.assert_called_once_with("Event 1")

    assert result == event



def test_get_by_title_raises_if_not_found(event_service, mock_event_repo):
    mock_event_repo.get_by_title.return_value = None

    with pytest.raises(EventNotFoundException, match="Event 1"):
        event_service.get_by_title("Event 1")

    mock_event_repo.get_by_title.assert_called_once_with("Event 1")


def test_get_by_category(event_service, mock_event_repo):
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    event = Event(id=1,
                  title='Event 1',
                  organizer=organizer,
                  datetime=datetime.now(),
                  description='Event description',
                  organizer_id=organizer.id,
                  location='Location 1',
                  category='category')
    mock_event_repo.get_by_category.return_value = event

    result = event_service.get_by_category("category")

    mock_event_repo.get_by_category.assert_called_once_with("category")
    assert result == event

def test_get_by_location(event_service, mock_event_repo):
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    event = Event(id=1,
                  title='Event 1',
                  organizer=organizer,
                  datetime=datetime.now(),
                  description='Event description',
                  organizer_id=organizer.id,
                  location='Location 1',
                  category='category')
    mock_event_repo.get_by_location.return_value = event

    result = event_service.get_by_location("Location 1")

    mock_event_repo.get_by_location.assert_called_once_with("Location 1")
    assert result == event

def test_get_by_date(event_service, mock_event_repo):
    datetime_now = datetime.now()

    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    event = Event(id=1,
                  title='Event 1',
                  organizer=organizer,
                  datetime=datetime_now,
                  description='Event description',
                  organizer_id=organizer.id,
                  location='Location 1',
                  category='category')
    mock_event_repo.get_by_date.return_value = event

    result = event_service.get_by_date(datetime_now)

    mock_event_repo.get_by_date.assert_called_once_with(datetime_now)
    assert result == event

def test_get_by_organizer_success(event_service, mock_user_repo, mock_event_repo):
    organizer = User(id=1, name="Name", surname="Surname", email="email@example.com", password="secret")
    event = Event(id=1,
                  title="Event 1",
                  organizer=organizer,
                  datetime=datetime.now(),
                  description="Event description",
                  organizer_id=organizer.id,
                  location="Location 1",
                  category="category")

    mock_user_repo.get_by_email.return_value = organizer
    mock_event_repo.get_by_organizer_id.return_value = [event]

    result = event_service.get_by_organizer("email@example.com")

    mock_user_repo.get_by_email.assert_called_once_with("email@example.com")
    mock_event_repo.get_by_organizer_id.assert_called_once_with(organizer.id)
    assert result == [event]


def test_get_by_organizer_raises_if_user_not_found(event_service, mock_user_repo):
    mock_user_repo.get_by_email.return_value = None

    with pytest.raises(UserNotFoundException, match="No user found with email email@example.com"):
        event_service.get_by_organizer("email@example.com")

    mock_user_repo.get_by_email.assert_called_once_with("email@example.com")


def test_get_all(event_service, mock_event_repo):
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

    mock_event_repo.get_all.assert_called_once()
    assert result == events


def test_create_event(event_service, mock_event_repo, mock_user_repo):
    # Arrange
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    mock_user_repo.get_by_email.return_value = organizer
    mock_event_repo.get_by_title.return_value = None

    payload = {
        'title':           'Event 1',
        'description':     'Event description',
        'datetime':        datetime.now(),
        'location':        'Location 1',
        'category':        'category',
        'organizer_email': organizer.email
    }
    saved_event = Event(
        title=payload['title'],
        description=payload['description'],
        datetime=payload['datetime'],
        location=payload['location'],
        category=payload['category'],
        organizer_id=organizer.id
    )
    mock_event_repo.save.return_value = saved_event

    # Act
    result = event_service.create(payload)

    # Assert
    assert isinstance(result, Event)
    assert result.title == 'Event 1'
    assert result.organizer_id == organizer.id


def test_create_raises_on_duplicate_title(event_service, mock_event_repo, mock_user_repo):
    # Arrange
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    mock_user_repo.get_by_email.return_value = organizer

    # Simulate an existing event with the same title
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

    # Act & Assert
    with pytest.raises(EventAlreadyExistsException) as exc:
        event_service.create(payload)
    assert 'DupEvent' in str(exc.value)


def test_delete_by_title_success(event_service, mock_event_repo):
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    event = Event(id=1,
                           title='Event 1',
                           organizer=organizer,
                           datetime=datetime.now(),
                           description='Event description',
                           organizer_id=organizer.id,
                           location='Location 1',
                           category='category')
    mock_event_repo.get_by_title.return_value = event
    result = event_service.get_by_title("Event 1")
    assert result == event

    event_service.delete_by_title("Event 1")
    mock_event_repo.delete_by_title.assert_called_once_with("Event 1")


def test_delete_by_title_raises_if_not_found(event_service, mock_event_repo):
    mock_event_repo.get_by_title.return_value = None

    with pytest.raises(EventNotFoundException, match="Event 1"):
        event_service.delete_by_title("Event 1")

def test_delete_by_title_wraps_repository_errors(event_service, mock_event_repo):
    """delete_by_title should catch exceptions from the repo and raise EventDeleteException."""
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    event = Event(id=1,
                  title='Event 1',
                  organizer=organizer,
                  datetime=datetime.now(),
                  description='Event description',
                  organizer_id=organizer.id,
                  location='Location 1',
                  category='category')

    mock_event_repo.get_by_title.return_value = event
    mock_event_repo.delete_by_title.side_effect = RuntimeError("db down")

    with pytest.raises(EventDeleteException) as ei:
        event_service.delete_by_title("Event 1")

    assert isinstance(ei.value.original_exception, RuntimeError)
    mock_event_repo.get_by_title.assert_called_once_with("Event 1")
    mock_event_repo.delete_by_title.assert_called_once_with("Event 1")


def test_create_wraps_repository_errors(event_service, mock_event_repo, mock_user_repo):
    # Arrange
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    mock_user_repo.get_by_email.return_value = organizer
    mock_event_repo.get_by_title.return_value = None
    mock_event_repo.save.side_effect = RuntimeError("db down")

    payload = {
        'title':           'CrashEvent',
        'description':     'desc',
        'datetime':        datetime.now(),
        'location':        'loc',
        'category':        'cat',
        'organizer_email': organizer.email
    }

    # Act & Assert
    with pytest.raises(EventSaveException) as exc:
        event_service.create(payload)
    assert str(exc.value) == 'Unable to save event due to an internal error.'



def test_update_success(event_service, mock_event_repo):
    """update should call save() on an existing event when no conflicts."""
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    event = Event(id=1,
                      title='Event 1',
                      organizer=organizer,
                      datetime=datetime.now(),
                      description='Event description',
                      organizer_id=organizer.id,
                      location='Location 1',
                      category='category')
    mock_event_repo.get_by_id.return_value = event
    mock_event_repo.get_by_title.return_value = event
    mock_event_repo.save.return_value = event
    result = event_service.update(event)
    mock_event_repo.save.assert_called_once_with(event)
    assert result is event

############

def test_update_raises_not_found(event_service, mock_event_repo):
    """update should raise EventNotFoundException if the event to update doesn’t exist."""
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')

    mock_event_repo.get_by_id.return_value = None
    with pytest.raises(EventNotFoundException):
        event_service.update(Event(id=1,
                      title='Event 1',
                      organizer=organizer,
                      datetime=datetime.now(),
                      description='Event description',
                      organizer_id=organizer.id,
                      location='Location 1',
                      category='category'))


def test_update_raises_duplicate_title(event_service, mock_event_repo):
    """update should raise EventAlreadyExists there is already an event with that title."""
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    original = Event(id=1,
                  title='Event 1',
                  organizer=organizer,
                  datetime=datetime.now(),
                  description='Event description',
                  organizer_id=organizer.id,
                  location='Location 1',
                  category='category')

    conflict = Event(id=2,
                     title='Event 1',
                     organizer=organizer,
                     datetime=datetime.now(),
                     description='Event description',
                     organizer_id=organizer.id,
                     location='Location 2',
                     category='category')
    mock_event_repo.get_by_id.return_value = original
    mock_event_repo.get_by_title.return_value = conflict
    with pytest.raises(EventAlreadyExistsException):
        event_service.update(original)


def test_update_wraps_save_errors(event_service, mock_event_repo):
    """update should catch repo.save exceptions and re-raise EventSaveException."""
    organizer = User(id=1, name='Name', surname='Surname', email='email', password='secret')
    event = Event(id=1,
                     title='Event 1',
                     organizer=organizer,
                     datetime=datetime.now(),
                     description='Event description',
                     organizer_id=organizer.id,
                     location='Location 1',
                     category='category')
    mock_event_repo.get_by_id.return_value = event
    mock_event_repo.get_by_title.return_value = event
    mock_event_repo.save.side_effect = ValueError("oops")
    with pytest.raises(EventSaveException) as ei:
        event_service.update(event)
    assert isinstance(ei.value.original_exception, ValueError)
