import pytest
from unittest.mock import MagicMock
from flask import Flask
from flask_restx import Api
from dependency_injector import providers
from marshmallow import ValidationError

from app.routes.event_route import event_ns
from app.container import Container

@pytest.fixture
def app():
    # Create Flask app and register namespace
    app = Flask(__name__)
    app.config['TESTING'] = True
    api = Api(app)
    api.add_namespace(event_ns, path='/events')

    # Override DI container providers at class level
    mock_event_service = MagicMock()
    Container.event_service.override(providers.Object(mock_event_service))
    mock_user_service = MagicMock()
    Container.user_service.override(providers.Object(mock_user_service))

    # Initialize and wire the container
    container = Container()
    container.init_resources()
    container.wire(packages=['app.routes'])

    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def test_get_all_events(client):
    # Arrange
    mock_service = Container.event_service()
    FakeEvent = type('FakeEvent', (), {})
    evt = FakeEvent()
    evt.id = 1
    evt.title = 'E1'
    evt.datetime = '2025-08-04 15:30:00'
    evt.description = 'desc'
    evt.location = 'loc'
    evt.category = 'cat'
    mock_service.get_all.return_value = [evt]

    # Act
    response = client.get('/events')

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert data[0]['title'] == 'E1'
    assert data[0]['description'] == 'desc'


def test_post_event_success(client):
    # Arrange
    mock_user_service = Container.user_service()
    mock_user = type('U', (), {'id': 42})
    mock_user_service.get_by_email.return_value = mock_user

    mock_event_service = Container.event_service()
    FakeEvent = type('FakeEvent', (), {})
    new_evt = FakeEvent()
    new_evt.id = 2
    new_evt.title = 'E2'
    new_evt.datetime = '2025-08-04 16:00:00'
    new_evt.description = 'desc2'
    new_evt.location = 'loc2'
    new_evt.category = 'cat2'
    mock_event_service.create.return_value = new_evt

    payload = {
        'title': 'E2',
        'description': 'desc2',
        'datetime': '2025-08-04 16:00:00',
        'location': 'loc2',
        'category': 'cat2',
        'organizer_email': 'alice@example.com'
    }

    # Act
    response = client.post('/events', json=payload)

    # Assert
    assert response.status_code == 201
    result = response.get_json()
    assert result['title'] == 'E2'
    assert result['datetime'] == '2025-08-04 16:00:00'
    assert 'id' not in result


def test_post_event_invalid_datetime_raises(client):
    # Arrange invalid datetime
    payload = {
        'title': 'E3',
        'description': 'desc3',
        'datetime': 'invalid-datetime',
        'location': 'loc3',
        'category': 'cat3',
        'organizer_email': 'alice@example.com'
    }
    # Ensure lookup would succeed if datetime valid
    Container.user_service().get_by_email.return_value = type('U2', (), {'id': 99})

    # Act & Assert
    with pytest.raises(ValidationError):
        client.post('/events', json=payload)


def test_post_event_user_not_found_raises(client):
    # Arrange payload with valid datetime
    payload = {
        'title': 'E4',
        'description': 'desc4',
        'datetime': '2025-08-04 17:00:00',
        'location': 'loc4',
        'category': 'cat4',
        'organizer_email': 'notfound@example.com'
    }
    # Simulate user lookup failure
    Container.user_service().get_by_email.side_effect = Exception('User not found')

    # Act & Assert
    with pytest.raises(Exception) as exc:
        client.post('/events', json=payload)
    assert 'User not found' in str(exc.value)
