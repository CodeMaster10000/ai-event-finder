import pytest
from unittest.mock import MagicMock, ANY
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.user_service_impl import UserServiceImpl
from app.error_handler.exceptions import (
    DuplicateEmailException,
    UserNotFoundException,
    UserSaveException,
    UserDeleteException,
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
    # Make services pass this object to repos for non-transactional calls
    from app import extensions as _ext
    monkeypatch.setattr(_ext.db, "session", fake_session)
    return fake_session

@pytest.fixture
def mock_user_repo():
    return MagicMock()

@pytest.fixture
def service(mock_user_repo):
    return UserServiceImpl(user_repository=mock_user_repo)

# -------------------------------
# Tests
# -------------------------------

def test_get_by_id_raises_not_found(service, mock_user_repo, patch_db_session):
    """get_by_id should raise UserNotFoundException when repo returns None."""
    mock_user_repo.get_by_id.return_value = None
    with pytest.raises(UserNotFoundException):
        service.get_by_id(123)
    mock_user_repo.get_by_id.assert_called_once_with(123, patch_db_session)


def test_get_by_email_raises_not_found(service, mock_user_repo, patch_db_session):
    """get_by_email should raise UserNotFoundException when repo returns None."""
    mock_user_repo.get_by_email.return_value = None
    with pytest.raises(UserNotFoundException):
        service.get_by_email("no@one.com")
    mock_user_repo.get_by_email.assert_called_once_with("no@one.com", patch_db_session)


def test_get_by_name_raises_not_found(service, mock_user_repo, patch_db_session):
    """get_by_name should raise UserNotFoundException when repo returns None."""
    mock_user_repo.get_by_name.return_value = None
    with pytest.raises(UserNotFoundException):
        service.get_by_name("Nobody")
    mock_user_repo.get_by_name.assert_called_once_with("Nobody", patch_db_session)


def test_save_wraps_repository_errors(service, mock_user_repo, patch_db_session):
    """save should catch any Exception from repo.save and re-raise as UserSaveException."""
    new_user = User(email="x@y.com", name="A", surname="B", password="pw123")
    mock_user_repo.get_by_email.return_value = None
    mock_user_repo.save.side_effect = RuntimeError("db down")

    with pytest.raises(UserSaveException) as ei:
        service.save(new_user)

    # save() is transactional → decorator provides its own session
    mock_user_repo.get_by_email.assert_called_once_with("x@y.com", ANY)
    mock_user_repo.save.assert_called_once_with(new_user, ANY)
    assert isinstance(ei.value.original_exception, RuntimeError)


def test_update_success(service, mock_user_repo, patch_db_session):
    """update should call save() on an existing user when no conflicts."""
    u = User(id=5, email="a@b.com", name="A", surname="B", password="pw123")
    mock_user_repo.get_by_id.return_value = u
    # pre-check for conflict → same user object, allowed
    mock_user_repo.get_by_email.return_value = u

    # return the user back from save
    mock_user_repo.save.side_effect = lambda user, session: user

    result = service.update(u)

    # get_by_id/get_by_email are invoked inside transactional wrapper too → ANY session
    mock_user_repo.get_by_id.assert_called_once_with(5, ANY)
    mock_user_repo.get_by_email.assert_called_once_with("a@b.com", ANY)
    mock_user_repo.save.assert_called_once_with(u, ANY)
    assert result is u


def test_update_raises_not_found(service, mock_user_repo, patch_db_session):
    """update should raise UserNotFoundException if the user to update doesn’t exist."""
    mock_user_repo.get_by_id.return_value = None
    with pytest.raises(UserNotFoundException):
        service.update(User(id=99, email="x@x.com", name="X", surname="X", password="pw"))
    # transactional → ANY session
    mock_user_repo.get_by_id.assert_called_once_with(99, ANY)


def test_update_raises_duplicate_email(service, mock_user_repo, patch_db_session):
    """update should raise DuplicateEmailException if email belongs to another user."""
    original = User(id=1, email="a@a.com", name="A", surname="A", password="pw")
    conflict  = User(id=2, email="a@a.com", name="B", surname="B", password="pw")
    mock_user_repo.get_by_id.return_value = original
    mock_user_repo.get_by_email.return_value = conflict

    with pytest.raises(DuplicateEmailException):
        service.update(original)

    mock_user_repo.get_by_id.assert_called_once_with(1, ANY)         # transactional
    mock_user_repo.get_by_email.assert_called_once_with("a@a.com", ANY)


def test_update_wraps_save_errors(service, mock_user_repo, patch_db_session):
    """update should catch repo.save exceptions and re-raise UserSaveException."""
    u = User(id=7, email="b@b.com", name="B", surname="B", password="pw123")
    mock_user_repo.get_by_id.return_value = u
    mock_user_repo.get_by_email.return_value = u
    mock_user_repo.save.side_effect = ValueError("oops")

    with pytest.raises(UserSaveException) as ei:
        service.update(u)

    mock_user_repo.get_by_id.assert_called_once_with(7, ANY)         # transactional
    mock_user_repo.get_by_email.assert_called_once_with("b@b.com", ANY)
    mock_user_repo.save.assert_called_once_with(u, ANY)
    assert isinstance(ei.value.original_exception, ValueError)


def test_delete_by_id_wraps_errors(service, mock_user_repo, patch_db_session):
    """delete_by_id should catch repo.delete_by_id exceptions and re-raise UserDeleteException."""
    u = User(id=8, email="c@c.com", name="C", surname="C", password="pw123")
    mock_user_repo.get_by_id.return_value = u
    mock_user_repo.delete_by_id.side_effect = KeyError("fail")

    with pytest.raises(UserDeleteException) as ei:
        service.delete_by_id(8)

    mock_user_repo.get_by_id.assert_called_once_with(8, ANY)         # transactional
    mock_user_repo.delete_by_id.assert_called_once_with(8, ANY)
    assert ei.value.user_id == 8


def test_exists_by_id_raises_not_found(service, mock_user_repo, patch_db_session):
    """exists_by_id should raise UserNotFoundException when the user is not found."""
    mock_user_repo.get_by_id.return_value = None
    with pytest.raises(UserNotFoundException):
        service.exists_by_id(42)
    # non-transactional path → uses patched db.session directly
    mock_user_repo.get_by_id.assert_called_once_with(42, patch_db_session)
