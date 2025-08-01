import pytest
from unittest.mock import MagicMock
from app.models.user import User
from app.services.user_service_impl import UserServiceImpl
from app.error_handler.exceptions import (
    DuplicateEmailException,
    UserNotFoundException,
    UserSaveException,
    UserDeleteException,
)

@pytest.fixture
def mock_user_repo():
    return MagicMock()

@pytest.fixture
def service(mock_user_repo):
    return UserServiceImpl(user_repository=mock_user_repo)


def test_get_by_id_raises_not_found(service, mock_user_repo):
    """get_by_id should raise UserNotFoundException when repo returns None."""
    mock_user_repo.get_by_id.return_value = None
    with pytest.raises(UserNotFoundException):
        service.get_by_id(123)


def test_get_by_email_raises_not_found(service, mock_user_repo):
    """get_by_email should raise UserNotFoundException when repo returns None."""
    mock_user_repo.get_by_email.return_value = None
    with pytest.raises(UserNotFoundException):
        service.get_by_email("no@one.com")


def test_get_by_name_raises_not_found(service, mock_user_repo):
    """get_by_name should raise UserNotFoundException when repo returns None."""
    mock_user_repo.get_by_name.return_value = None
    with pytest.raises(UserNotFoundException):
        service.get_by_name("Nobody")


def test_save_wraps_repository_errors(service, mock_user_repo):
    """save should catch any Exception from repo.save and re-raise as UserSaveException."""
    new_user = User(email="x@y.com", name="A", surname="B", password="pw123")
    mock_user_repo.get_by_email.return_value = None
    mock_user_repo.save.side_effect = RuntimeError("db down")
    with pytest.raises(UserSaveException) as ei:
        service.save(new_user)
    assert isinstance(ei.value.original_exception, RuntimeError)


def test_update_success(service, mock_user_repo):
    """update should call save() on an existing user when no conflicts."""
    u = User(id=5, email="a@b.com", name="A", surname="B", password="pw123")
    mock_user_repo.get_by_id.return_value = u
    mock_user_repo.get_by_email.return_value = u
    mock_user_repo.save.return_value = u
    result = service.update(u)
    mock_user_repo.save.assert_called_once_with(u)
    assert result is u


def test_update_raises_not_found(service, mock_user_repo):
    """update should raise UserNotFoundException if the user to update doesn’t exist."""
    mock_user_repo.get_by_id.return_value = None
    with pytest.raises(UserNotFoundException):
        service.update(User(id=99, email="x@x.com", name="X", surname="X", password="pw"))


def test_update_raises_duplicate_email(service, mock_user_repo):
    """update should raise DuplicateEmailException if email belongs to another user."""
    original = User(id=1, email="a@a.com", name="A", surname="A", password="pw")
    conflict  = User(id=2, email="a@a.com", name="B", surname="B", password="pw")
    mock_user_repo.get_by_id.return_value = original
    mock_user_repo.get_by_email.return_value = conflict
    with pytest.raises(DuplicateEmailException):
        service.update(original)


def test_update_wraps_save_errors(service, mock_user_repo):
    """update should catch repo.save exceptions and re-raise UserSaveException."""
    u = User(id=7, email="b@b.com", name="B", surname="B", password="pw123")
    mock_user_repo.get_by_id.return_value = u
    mock_user_repo.get_by_email.return_value = u
    mock_user_repo.save.side_effect = ValueError("oops")
    with pytest.raises(UserSaveException) as ei:
        service.update(u)
    assert isinstance(ei.value.original_exception, ValueError)


def test_delete_by_id_wraps_errors(service, mock_user_repo):
    """delete_by_id should catch repo.delete_by_id exceptions and re-raise UserDeleteException."""
    u = User(id=8, email="c@c.com", name="C", surname="C", password="pw123")
    mock_user_repo.get_by_id.return_value = u
    mock_user_repo.delete_by_id.side_effect = KeyError("fail")
    with pytest.raises(UserDeleteException) as ei:
        service.delete_by_id(8)
    assert ei.value.user_id == 8


def test_exists_by_id_raises_not_found(service, mock_user_repo):
    """exists_by_id should raise UserNotFoundException when the user is not found."""
    mock_user_repo.get_by_id.return_value = None
    with pytest.raises(UserNotFoundException):
        service.exists_by_id(42)
