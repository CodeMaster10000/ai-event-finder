from unittest.mock import MagicMock

import pytest
from flask import Flask
from werkzeug.exceptions import HTTPException

from app.models.user import User
from app.routes.user_route import (
    user_ns,
    UserBaseResource,
    UserByIdResource,
    UserByEmailResource,
    UsersByNameResource,
    ExistsByIdResource,
    ExistsByNameResource
)
from app.routes.user_route import user_schema, users_schema
from app.services.user_service import AbstractUserService


@pytest.fixture
def app():
    """Create and configure a new Flask app instance for each test."""
    app = Flask(__name__)
    # Register namespace routes for completeness (optional here)
    from flask_restx import Api
    api = Api(app)
    api.add_namespace(user_ns)
    return app

@pytest.fixture
def user_service_mock():
    """A mock of the AbstractUserService."""
    return MagicMock(spec=AbstractUserService)

def test_get_all_users_empty(app, user_service_mock):
    # Service returns empty list
    user_service_mock.get_all.return_value = []
    with app.test_request_context():
        resource = UserBaseResource()
        result, status = resource.get(user_service=user_service_mock)
    assert status == 200
    assert result == []
    user_service_mock.get_all.assert_called_once()

def test_get_all_users_nonempty(app, user_service_mock):
    # Prepare two users
    u1 = User(id=1, name='John', surname='Doe', email='john@example.com', password='secret')
    u2 = User(id=2, name='Jane', surname='Smith', email='jane@example.com', password='hunter2')
    user_service_mock.get_all.return_value = [u1, u2]
    with app.test_request_context():
        resource = UserBaseResource()
        result, status = resource.get(user_service=user_service_mock)
    assert status == 200
    # Verify serialization
    assert result == users_schema.dump([u1, u2])

def test_post_user_success(app, user_service_mock):
    input_data = {
        'name': 'Alice',
        'surname': 'Wonder',
        'email': 'alice@example.com',
        'password': 'Password1'
    }
    # The service.save receives a User instance and returns one with an id
    saved = User(id=3, name='Alice', surname='Wonder', email='alice@example.com', password='Password1')
    user_service_mock.save.return_value = saved
    with app.test_request_context(json=input_data):
        resource = UserBaseResource()
        response, status = resource.post(user_service=user_service_mock)
    assert status == 201
    assert response == user_schema.dump(saved)
    user_service_mock.save.assert_called_once()

@ pytest.mark.parametrize("missing_field", ['name', 'surname', 'email', 'password'])
def test_post_user_validation_error(app, user_service_mock, missing_field):
    # Remove one required field to trigger validation error
    data = {
        'name': 'Bob', 'surname': 'Builder', 'email': 'bob@example.com', 'password': 'Password1'
    }
    data.pop(missing_field)
    with app.test_request_context(json=data):
        resource = UserBaseResource()
        with pytest.raises(HTTPException) as excinfo:
            resource.post(user_service=user_service_mock)
        assert excinfo.value.code == 400

@pytest.mark.parametrize("user_id, exists", [(1, True), (2, False)])
def test_exists_by_id(app, user_service_mock, user_id, exists):
    user_service_mock.exists_by_id.return_value = exists
    with app.test_request_context():
        resource = ExistsByIdResource()
        response, status = resource.get(user_id=user_id, user_service=user_service_mock)
    assert status == 200
    assert response == {'exists': exists}

@pytest.mark.parametrize("name, exists", [('Alice', True), ('Nemo', False)])
def test_exists_by_name(app, user_service_mock, name, exists):
    user_service_mock.exists_by_name.return_value = exists
    with app.test_request_context():
        resource = ExistsByNameResource()
        response, status = resource.get(name=name, user_service=user_service_mock)
    assert status == 200
    assert response == {'exists': exists}

@pytest.mark.parametrize("user_id, found", [(1, True), (99, False)])
def test_get_by_id(app, user_service_mock, user_id, found):
    if found:
        user = User(id=user_id, name='Test', surname='User', email='test@example.com', password='X')
        user_service_mock.get_by_id.return_value = user
        with app.test_request_context():
            resource = UserByIdResource()
            response, status = resource.get(user_id=user_id, user_service=user_service_mock)
        assert status == 200
        assert response == user_schema.dump(user)
    else:
        user_service_mock.get_by_id.return_value = None
        with app.test_request_context():
            resource = UserByIdResource()
            with pytest.raises(HTTPException) as excinfo:
                resource.get(user_id=user_id, user_service=user_service_mock)
        assert excinfo.value.code == 404

@pytest.mark.parametrize("user_id, found", [(1, True), (5, False)])
def test_delete_by_id(app, user_service_mock, user_id, found):
    if found:
        # Simulate deletion: get_by_id returns a user
        user = User(id=user_id, name='A', surname='B', email='a@b.com', password='X')
        user_service_mock.get_by_id.return_value = user
        with app.test_request_context():
            resource = UserByIdResource()
            response, status = resource.delete(user_id=user_id, user_service=user_service_mock)
        assert status == 204
    else:
        user_service_mock.get_by_id.return_value = None
        with app.test_request_context():
            resource = UserByIdResource()
            with pytest.raises(HTTPException) as excinfo:
                resource.delete(user_id=user_id, user_service=user_service_mock)
        assert excinfo.value.code == 404

@pytest.mark.parametrize("email, found", [('john@example.com', True), ('foo@bar.com', False)])
def test_get_by_email(app, user_service_mock, email, found):
    if found:
        user = User(id=7, name='J', surname='D', email=email, password='X')
        user_service_mock.get_by_email.return_value = user
        with app.test_request_context():
            resource = UserByEmailResource()
            response, status = resource.get(email=email, user_service=user_service_mock)
        assert status == 200
        assert response == user_schema.dump(user)
    else:
        user_service_mock.get_by_email.return_value = None
        with app.test_request_context():
            resource = UserByEmailResource()
            with pytest.raises(HTTPException) as excinfo:
                resource.get(email=email, user_service=user_service_mock)
        assert excinfo.value.code == 404

@pytest.mark.parametrize("name, found", [('Alice', True), ('Bob', False)])
def test_get_by_name(app, user_service_mock, name, found):
    if found:
        user = User(id=10, name=name, surname='X', email='x@y.com', password='X')
        user_service_mock.get_by_name.return_value = user
        with app.test_request_context():
            resource = UsersByNameResource()
            response, status = resource.get(name=name, user_service=user_service_mock)
        assert status == 200
        assert response == user_schema.dump(user)
    else:
        user_service_mock.get_by_name.return_value = None
        with app.test_request_context():
            resource = UsersByNameResource()
            with pytest.raises(HTTPException) as excinfo:
                resource.get(name=name, user_service=user_service_mock)
        assert excinfo.value.code == 404
