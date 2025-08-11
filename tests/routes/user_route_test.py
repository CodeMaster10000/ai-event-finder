from unittest.mock import MagicMock

import pytest
from marshmallow import ValidationError

from app.models.user import User
from app.routes.user_route import (
    UserBaseResource,
    UserByIdResource,
    UserByEmailResource,
    UsersByNameResource,
    ExistsByIdResource,
    ExistsByNameResource
)
from app.routes.user_route import user_schema, users_schema
from app.util.test_jwt_token_util import generate_test_token
from app.services.user_service import UserService
from app.extensions import jwt
from app import create_app

@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "JWT_SECRET_KEY": "test-secret-key",
    })
    jwt.init_app(app)
    with app.app_context():
        yield app

@pytest.fixture
def auth_header(app):
    token = generate_test_token(app, user_id=1)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def user_service_mock():
    """A mock of the UserService."""
    return MagicMock(spec=UserService)

def test_get_all_users_empty(app, user_service_mock, auth_header):
    # Service returns empty list
    user_service_mock.get_all.return_value = []
    with app.test_request_context(headers=auth_header):
        resource = UserBaseResource()
        result, status = resource.get(user_service=user_service_mock)
    assert status == 200
    assert result == []
    user_service_mock.get_all.assert_called_once()

def test_get_all_users_nonempty(app, user_service_mock, auth_header):
    # Prepare two users
    u1 = User(id=1, name='John', surname='Doe', email='john@example.com', password='secret')
    u2 = User(id=2, name='Jane', surname='Smith', email='jane@example.com', password='hunter2')
    user_service_mock.get_all.return_value = [u1, u2]
    with app.test_request_context(headers=auth_header):
        resource = UserBaseResource()
        result, status = resource.get(user_service=user_service_mock)
    assert status == 200
    # Verify serialization
    assert result == users_schema.dump([u1, u2])

def test_post_user_success(app, user_service_mock, auth_header):
    input_data = {
        'name': 'Alice',
        'surname': 'Wonder',
        'email': 'alice@example.com',
        'password': 'Password1'
    }
    # The service.save receives a User instance and returns one with an id
    saved = User(id=3, name='Alice', surname='Wonder', email='alice@example.com', password='Password1')
    user_service_mock.save.return_value = saved
    with app.test_request_context(json=input_data, headers=auth_header):
        resource = UserBaseResource()
        response, status = resource.post(user_service=user_service_mock)
    assert status == 201
    assert response == user_schema.dump(saved)
    user_service_mock.save.assert_called_once()

@pytest.mark.parametrize("missing_field", ["name", "surname", "email", "password"])
def test_post_user_validation_error(app, user_service_mock, missing_field, auth_header):
    data = {
        "name": "Bob",
        "surname": "Builder",
        "email": "bob@example.com",
        "password": "Password1",
    }
    data.pop(missing_field)

    with app.test_request_context(json=data, headers=auth_header):
        resource = UserBaseResource()
        with pytest.raises(ValidationError):
            resource.post(user_service=user_service_mock)

@pytest.mark.parametrize("user_id, exists", [(1, True), (2, False)])
def test_exists_by_id(app, user_service_mock, user_id, exists, auth_header):
    user_service_mock.exists_by_id.return_value = exists
    with app.test_request_context(headers=auth_header):
        resource = ExistsByIdResource()
        response, status = resource.get(user_id=user_id, user_service=user_service_mock)
    assert status == 200
    assert response == {'exists': exists}

@pytest.mark.parametrize("name, exists", [('Alice', True), ('Nemo', False)])
def test_exists_by_name(app, user_service_mock, name, exists, auth_header):
    user_service_mock.exists_by_name.return_value = exists
    with app.test_request_context(headers=auth_header):
        resource = ExistsByNameResource()
        response, status = resource.get(name=name, user_service=user_service_mock)
    assert status == 200
    assert response == {'exists': exists}

@pytest.mark.parametrize("user_id, found", [(1, True), (99, False)])
def test_get_by_id(app, user_service_mock, user_id, found, auth_header):
    if found:
        user = User(id=user_id, name='Test', surname='User', email='test@example.com', password='X')
        user_service_mock.get_by_id.return_value = user
        with app.test_request_context(headers=auth_header):
            resource = UserByIdResource()
            response, status = resource.get(user_id=user_id, user_service=user_service_mock)
        assert status == 200
        assert response == user_schema.dump(user)

@pytest.mark.parametrize("user_id, found", [(1, True), (5, False)])
def test_delete_by_id(app, user_service_mock, user_id, found, auth_header):
    if found:
        # Simulate deletion: get_by_id returns a user
        user = User(id=user_id, name='A', surname='B', email='a@b.com', password='X')
        user_service_mock.get_by_id.return_value = user
        with app.test_request_context(headers=auth_header):
            resource = UserByIdResource()
            response, status = resource.delete(user_id=user_id, user_service=user_service_mock)
        assert status == 204

@pytest.mark.parametrize("email, found", [('john@example.com', True), ('foo@bar.com', False)])
def test_get_by_email(app, user_service_mock, email, found, auth_header):
    if found:
        user = User(id=7, name='J', surname='D', email=email, password='X')
        user_service_mock.get_by_email.return_value = user
        with app.test_request_context(headers=auth_header):
            resource = UserByEmailResource()
            response, status = resource.get(email=email, user_service=user_service_mock)
        assert status == 200
        assert response == user_schema.dump(user)

@pytest.mark.parametrize("name, found", [('Alice', True), ('Bob', False)])
def test_get_by_name(app, user_service_mock, name, found, auth_header):
    if found:
        user = User(id=10, name=name, surname='X', email='x@y.com', password='X')
        user_service_mock.get_by_name.return_value = user
        with app.test_request_context(headers=auth_header):
            resource = UsersByNameResource()
            response, status = resource.get(name=name, user_service=user_service_mock)
        assert status == 200
        assert response == user_schema.dump(user)

def test_get_by_id_not_found(app, user_service_mock, auth_header):
    # Service returns None
    user_service_mock.get_by_id.return_value = None
    with app.test_request_context(headers=auth_header):
        resource = UserByIdResource()
        result, status = resource.get(user_id=42, user_service=user_service_mock)

    assert status == 200
#    assert result is None
    user_service_mock.get_by_id.assert_called_once_with(42)

def test_delete_by_id_not_found(app, user_service_mock, auth_header):
    # Service returns None, but delete is still invoked
    user_service_mock.get_by_id.return_value = None
    with app.test_request_context(headers=auth_header):
        resource = UserByIdResource()
        body, status = resource.delete(user_id=99, user_service=user_service_mock)

    assert status == 204
    assert body == ''
    user_service_mock.get_by_id.assert_called_once_with(99)
    user_service_mock.delete_by_id.assert_called_once_with(99)

def test_get_by_email_not_found(app, user_service_mock, auth_header):
    user_service_mock.get_by_email.return_value = None
    with app.test_request_context(headers=auth_header):
        resource = UserByEmailResource()
        result, status = resource.get(email="noone@example.com", user_service=user_service_mock)

    assert status == 200
    assert result is None
    user_service_mock.get_by_email.assert_called_once_with("noone@example.com")

def test_get_by_name_not_found(app, user_service_mock, auth_header):
    user_service_mock.get_by_name.return_value = None
    with app.test_request_context(headers=auth_header):
        resource = UsersByNameResource()
        result, status = resource.get(name="Nobody", user_service=user_service_mock)

    assert status == 200
    assert result is None
    user_service_mock.get_by_name.assert_called_once_with("Nobody")
