# tests/routes/test_events_and_auth_http.py

import pytest
from unittest.mock import MagicMock
from datetime import datetime
from dependency_injector import providers
from flask_jwt_extended import create_access_token

from app import create_app
from app.container import Container
from app.extensions import db as _db
from app.models.user import User
from app.models.event import Event
from tests.util.util_test import test_cfg


@pytest.fixture
def mock_event_service():
    svc = MagicMock()
    svc.get_all.return_value = [
        Event(
            id=1,
            title="Test Event",
            description="An event for testing",
            datetime=datetime.now(),
            location="Skopje",
            category="Tech",
            organizer_id=1,
        )
    ]
    # First pass (helps when running this file alone)
    Container.event_service.override(providers.Object(svc))
    yield svc
    try:
        Container.event_service.reset_override()
    except Exception:
        pass

@pytest.fixture(autouse=True)
def _reset_container_between_tests():
    # Run test
    yield
    # HARD reset after every test to avoid cross-module leakage
    try:
        Container.unwire()
    except Exception:
        pass
    for p in (
        getattr(Container, "event_service", None),
        getattr(Container, "user_service", None),
        getattr(Container, "embedding_service", None),
    ):
        if isinstance(p, providers.Provider):
            try:
                p.reset_override()
            except Exception:
                pass
    try:
        Container.reset_singletons()
    except Exception:
        pass

@pytest.fixture(scope="function")
def app(mock_event_service):
    # Re-apply override *right here* to beat any earlier wiring from other test modules
    Container.event_service.override(providers.Object(mock_event_service))

    app = create_app(test_cfg)
    with app.app_context():
        yield app

    # Teardown: reset override to avoid leaking into other modules
    try:
        Container.event_service.reset_override()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def clean_db(app):
    with app.app_context():
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_header(app):
    with app.app_context():
        token = create_access_token(identity="1", fresh=True)
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user_record(app):
    with app.app_context():
        user = User(name="Test", surname="User", email="test@example.com", password="testpass")
        _db.session.add(user)
        _db.session.commit()
        _db.session.refresh(user)
        _db.session.expunge(user)
        return user


def test_get_all_events_authorized(client, auth_header):
    resp = client.get("/events", headers=auth_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == "Test Event"


def test_get_all_events_unauthorized(client):
    resp = client.get("/events")
    assert resp.status_code == 401


def test_login_success(client, test_user_record):
    resp = client.post("/auth/login", json={"email": "test@example.com", "password": "testpass"})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert "access_token" in data and isinstance(data["access_token"], str)


def test_login_invalid_password(client, test_user_record):
    resp = client.post("/auth/login", json={"email": "test@example.com", "password": "wrongpass"})
    assert resp.status_code == 401, resp.get_data(as_text=True)
    assert resp.get_json()["message"] == "Invalid credentials"


def test_login_nonexistent_user(client):
    resp = client.post("/auth/login", json={"email": "nonexistent@example.com", "password": "nopass"})
    assert resp.status_code == 401, resp.get_data(as_text=True)
    assert resp.get_json()["message"] == "Invalid credentials"


def test_login_missing_fields(client):
    resp = client.post("/auth/login", json={"email": "test@example.com"})
    assert resp.status_code in (400, 422)


def test_login_no_payload(client):
    resp = client.post("/auth/login", json={})
    assert resp.status_code in (400, 422)
