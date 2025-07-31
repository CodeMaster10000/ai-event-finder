"""
Unit tests for the UserServiceImpl class.

These tests mock the UserRepository to verify business logic in isolation,
including proper exception handling and delegation of operations.
"""

import pytest
from unittest.mock import MagicMock
from app.models.user import User
from app.services.user_service_impl import UserServiceImpl
from app.error_handler.exceptions import DuplicateEmailException, UserNotFoundException


@pytest.fixture
def mock_user_repo():
    return MagicMock()


@pytest.fixture
def user_service(mock_user_repo):
    return UserServiceImpl(user_repository=mock_user_repo)


def test_get_by_id(user_service, mock_user_repo):
    user = User(id=1, name="Ana", surname="Ilievska", email="ana@example.com", password="secret")
    mock_user_repo.get_by_id.return_value = user

    result = user_service.get_by_id(1)

    mock_user_repo.get_by_id.assert_called_once_with(1)
    assert result == user


def test_get_by_email(user_service, mock_user_repo):
    user = User(id=2, name="Bob", surname="Smith", email="bob@example.com", password="pass")
    mock_user_repo.get_by_email.return_value = user

    result = user_service.get_by_email("bob@example.com")

    mock_user_repo.get_by_email.assert_called_once_with("bob@example.com")
    assert result == user


def test_get_by_name(user_service, mock_user_repo):
    user = User(id=3, name="Charlie", surname="Green", email="charlie@example.com", password="pw")
    mock_user_repo.get_by_name.return_value = user

    result = user_service.get_by_name("Charlie")

    mock_user_repo.get_by_name.assert_called_once_with("Charlie")
    assert result == user


def test_get_all(user_service, mock_user_repo):
    users = [
        User(id=1, name="Ana", surname="Ilievska", email="ana@example.com", password="a"),
        User(id=2, name="Bob", surname="Smith", email="bob@example.com", password="b")
    ]
    mock_user_repo.get_all.return_value = users

    result = user_service.get_all()

    mock_user_repo.get_all.assert_called_once()
    assert result == users


def test_save_creates_user(user_service, mock_user_repo):
    new_user = User(id=5, name="David", surname="Lee", email="david@example.com", password="pass")
    mock_user_repo.get_by_email.return_value = None
    mock_user_repo.save.return_value = new_user

    result = user_service.save(new_user)

    mock_user_repo.get_by_email.assert_called_once_with("david@example.com")
    mock_user_repo.save.assert_called_once_with(new_user)
    assert result == new_user


def test_save_raises_on_duplicate_email(user_service, mock_user_repo):
    existing_user = User(id=10, name="Ana", surname="Ilievska", email="ana@example.com", password="pw")
    new_user = User(id=11, name="New Ana", surname="Dup", email="ana@example.com", password="pw2")

    mock_user_repo.get_by_email.return_value = existing_user

    with pytest.raises(DuplicateEmailException, match="already exists"):
        user_service.save(new_user)


def test_delete_by_id_success(user_service, mock_user_repo):
    # Now delete_by_id uses get_by_id internally
    user = User(id=1, name="Test", surname="User", email="test@example.com", password="pw")
    mock_user_repo.get_by_id.return_value = user

    user_service.delete_by_id(1)

    mock_user_repo.get_by_id.assert_called_once_with(1)
    mock_user_repo.delete_by_id.assert_called_once_with(1)


def test_delete_by_id_raises_if_not_found(user_service, mock_user_repo):
    mock_user_repo.get_by_id.return_value = None

    with pytest.raises(UserNotFoundException, match="id=999"):
        user_service.delete_by_id(999)


def test_exists_by_id_returns_true(user_service, mock_user_repo):
    user = User(id=5, name="Test", surname="User", email="a@a.com", password="p")
    mock_user_repo.get_by_id.return_value = user

    result = user_service.exists_by_id(5)

    mock_user_repo.get_by_id.assert_called_once_with(5)
    assert result is True


def test_exists_by_name_raises_if_not_found(user_service, mock_user_repo):
    mock_user_repo.get_by_name.return_value = None

    with pytest.raises(UserNotFoundException, match="name=Alice"):
        user_service.exists_by_name("Alice")


def test_exists_by_name_returns_true(user_service, mock_user_repo):
    user = User(id=7, name="Alice", surname="Test", email="alice@test.com", password="p")
    mock_user_repo.get_by_name.return_value = user

    result = user_service.exists_by_name("Alice")

    mock_user_repo.get_by_name.assert_called_once_with("Alice")
    assert result is True
