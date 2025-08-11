import pytest
from unittest.mock import MagicMock
from datetime import datetime

from dependency_injector import providers
from app import create_app
from app.container import Container
from app.models.user import User
from app.models.event import Event
from app.extensions import db


# fixtures
@pytest.fixture
def test_user():
    return User(id=1, name="Test", surname="User", email="test@example.com", password="testpass")


@pytest.fixture
def test_event():
    return Event(
        id=1,
        title="Test Event",
        description="An event for testing",
        datetime=datetime.now(),
        location="Skopje",
        category="Tech",
        organizer_id=1
    )


@pytest.fixture
def mock_event_service(test_event):
    service = MagicMock()
    service.get_all.return_value = [test_event]
    Container.event_service.override(providers.Object(service))
    return service



@pytest.fixture
def app(mock_event_service):
    app = create_app({
        "TESTING": True,
        "JWT_SECRET_KEY": "test-secret-key",
    })
    # you can configure seperate test db
    # app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:postgres@localhost/ai_event_test"

    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_header(app, test_user):
    with app.app_context():
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity=str(test_user.id))
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user_record(app):
    with app.app_context():
        # check and delete any existing user with same email
        existing_user = db.session.query(User).filter_by(email="test@example.com").first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()

        # create and return the test user
        user = User(name="Test", surname="User", email="test@example.com", password="testpass")
        db.session.add(user)
        db.session.commit()
        return user

# tests

def test_get_all_events_authorized(client, auth_header):
    response = client.get("/events", headers=auth_header)

    print("Response JSON:", response.get_json())
    print("Status Code:", response.status_code)

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert data[0]["title"] == "Test Event"


def test_get_all_events_unauthorized(client):
    response = client.get("/events")  # No token sent

    assert response.status_code == 401

def test_login_success(client, test_user_record):
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "testpass"
    })

    data = response.get_json()
    assert response.status_code == 200
    assert "access_token" in data
    assert isinstance(data["access_token"], str)

def test_login_invalid_password(client, test_user_record):
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpass"
    })
    data = response.get_json()
    assert response.status_code == 401
    assert data["message"] == "Invalid credentials"

def test_login_nonexistent_user(client):
    response = client.post("/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "nopass"
    })
    data = response.get_json()
    assert response.status_code == 401
    assert data["message"] == "Invalid credentials"

def test_login_missing_fields(client):
    response = client.post("/auth/login", json={"email": "test@example.com"})
    assert response.status_code in (400, 422)

def test_login_no_payload(client):
    response = client.post("/auth/login", json={})
    assert response.status_code in (400, 422)

