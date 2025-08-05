import pytest
from unittest.mock import MagicMock
from sqlalchemy.exc import IntegrityError
from psycopg2.errors import UniqueViolation
from app.services.app_service_impl import AppServiceImpl
from app.error_handler.exceptions import (
    UserAlreadyInEventException,
    UserNotInEventException,
    UserNotFoundException,
    EventNotFoundException
)


# ——— Dummy domain classes ——————————————————————————————————

class DummyUser:
    def __init__(self, email):
        self.email = email

    def __eq__(self, other):
        return isinstance(other, DummyUser) and other.email == self.email

    def __repr__(self):
        return f"<DummyUser {self.email}>"


class DummyEvent:
    def __init__(self, title):
        self.title = title
        self.guests = []

    def __repr__(self):
        return f"<DummyEvent {self.title}>"


# ——— Fixtures ——————————————————————————————————————————————

@pytest.fixture
def mock_user_repo():
    return MagicMock()


@pytest.fixture
def mock_event_repo():
    return MagicMock()


@pytest.fixture
def service(mock_user_repo, mock_event_repo):
    return AppServiceImpl(
        user_repo=mock_user_repo,
        event_repo=mock_event_repo
    )


# ——— Tests ——————————————————————————————————————————————

def test_add_participant_success(service, mock_user_repo, mock_event_repo):
    """Should append user to event and call save()."""
    user = DummyUser("u@example.com")
    event = DummyEvent("MyEvent")
    mock_event_repo.get_by_title.return_value = event
    mock_user_repo.get_by_email.return_value = user

    service.add_participant_to_event("MyEvent", "u@example.com")

    assert user in event.guests
    mock_event_repo.save.assert_called_once_with(event)


def test_add_participant_event_not_found(service, mock_user_repo, mock_event_repo):
    """Should raise EventNotFoundException if event missing."""
    mock_event_repo.get_by_title.return_value = None

    with pytest.raises(EventNotFoundException):
        service.add_participant_to_event("Unknown", "u@example.com")


def test_add_participant_user_not_found(service, mock_user_repo, mock_event_repo):
    """Should raise UserNotFoundException if user missing."""
    event = DummyEvent("MyEvent")
    mock_event_repo.get_by_title.return_value = event
    mock_user_repo.get_by_email.return_value = None

    with pytest.raises(UserNotFoundException):
        service.add_participant_to_event("MyEvent", "u@example.com")


def test_add_participant_already_exists(service, mock_user_repo, mock_event_repo):
    """Should raise UserAlreadyInEventException if user already in participants."""
    user = DummyUser("u@example.com")
    event = DummyEvent("MyEvent")
    event.guests.append(user)
    mock_event_repo.get_by_title.return_value = event
    mock_user_repo.get_by_email.return_value = user

    with pytest.raises(UserAlreadyInEventException):
        service.add_participant_to_event("MyEvent", "u@example.com")


def test_add_participant_integrity_error_translated(service, mock_user_repo, mock_event_repo):
    """Should translate DB IntegrityError into UserAlreadyInEventException."""
    user = DummyUser("u@example.com")
    event = DummyEvent("MyEvent")
    mock_event_repo.get_by_title.return_value = event
    mock_user_repo.get_by_email.return_value = user

    mock_event_repo.save.side_effect = IntegrityError("INSERT ...", {}, UniqueViolation())

    with pytest.raises(UserAlreadyInEventException):
        service.add_participant_to_event("MyEvent", "u@example.com")


def test_remove_participant_success(service, mock_user_repo, mock_event_repo):
    """Should remove user from participants and call save()."""
    user = DummyUser("u@example.com")
    event = DummyEvent("MyEvent")
    event.guests.append(user)
    mock_event_repo.get_by_title.return_value = event
    mock_user_repo.get_by_email.return_value = user

    service.remove_participant_from_event("MyEvent", "u@example.com")

    assert user not in event.guests
    mock_event_repo.save.assert_called_once_with(event)


def test_remove_participant_event_not_found(service, mock_user_repo, mock_event_repo):
    """Should raise EventNotFoundException if event missing on remove."""
    mock_event_repo.get_by_title.return_value = None

    with pytest.raises(EventNotFoundException):
        service.remove_participant_from_event("Unknown", "u@example.com")


def test_remove_participant_user_not_found(service, mock_user_repo, mock_event_repo):
    """Should raise UserNotFoundException if user missing on remove."""
    event = DummyEvent("MyEvent")
    mock_event_repo.get_by_title.return_value = event
    mock_user_repo.get_by_email.return_value = None

    with pytest.raises(UserNotFoundException):
        service.remove_participant_from_event("MyEvent", "u@example.com")


def test_remove_participant_not_in_event(service, mock_user_repo, mock_event_repo):
    """Should raise UserNotInEventException if user not already in participants."""
    user = DummyUser("u@example.com")
    event = DummyEvent("MyEvent")
    mock_event_repo.get_by_title.return_value = event
    mock_user_repo.get_by_email.return_value = user

    with pytest.raises(UserNotInEventException):
        service.remove_participant_from_event("MyEvent", "u@example.com")


def test_list_participants_success(service, mock_user_repo, mock_event_repo):
    """Should return the list of current participants."""
    event = DummyEvent("MyEvent")
    u1 = DummyUser("a@a.com")
    u2 = DummyUser("b@b.com")
    event.guests.extend([u1, u2])
    mock_event_repo.get_by_title.return_value = event

    result = service.list_participants("MyEvent")
    assert result == [u1, u2]


def test_list_participants_event_not_found(service, mock_user_repo, mock_event_repo):
    """Should raise EventNotFoundException if event missing on list."""
    mock_event_repo.get_by_title.return_value = None

    with pytest.raises(EventNotFoundException):
        service.list_participants("Unknown")
