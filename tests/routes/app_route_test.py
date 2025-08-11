from unittest.mock import MagicMock

import pytest

from app import create_app
from app.routes.app_route import ParticipantResource, ListParticipantsResource
from app.services.app_service import AppService
from app.services.model.model_service import ModelService
from app.util.test_jwt_token_util import generate_test_token


@pytest.fixture
def app():
    app = create_app({"TESTING": True})
    yield app

@pytest.fixture
def auth_header(app):
    token = generate_test_token(app, user_id=1)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def mock_app_service():
    return MagicMock(spec=AppService)

@pytest.fixture
def mock_model_service():
    # create a fake ModelService with the right interface
    return MagicMock(spec=ModelService)

# ADD PARTICIPANT TO EVENT (POST)

def test_add_participant_to_event_success(app, mock_app_service, auth_header):
    event_title = "event_1"
    user_email = "participant@example.com"

    with app.test_request_context(headers=auth_header):
        resource = ParticipantResource()
        mock_app_service.add_participant_to_event.return_value = None

        response, status = resource.post(
            event_title=event_title,
            user_email=user_email,
            app_service=mock_app_service
        )

        assert status == 201
        assert f"User '{user_email}' successfully added to event '{event_title}'" in response["message"]
        mock_app_service.add_participant_to_event.assert_called_once_with(
            "event_1", "participant@example.com"
        )

# REMOVE PARTICIPANT FROM EVENT (DELETE)

def test_remove_participant_from_event_success(app, mock_app_service, auth_header):
    event_title = "event_1"
    user_email = "participant@example.com"
    with app.test_request_context(headers=auth_header):
        resource = ParticipantResource()
        mock_app_service.remove_participant_from_event.return_value = None

        response, status = resource.delete(
            event_title="event_1",
            user_email="participant@example.com",
            app_service=mock_app_service
        )

        assert status == 200
        assert f"User '{user_email}' removed from event '{event_title}'" in response["message"]
        mock_app_service.remove_participant_from_event.assert_called_once_with(
            "event_1", "participant@example.com"
        )

# LIST PARTICIPANTS (GET)

def test_list_participants_success(app, mock_app_service, auth_header):
    from app.models.user import User  # Import your User model
    user1 = User(id=1, name="Ana", surname="Gjurchinova", email="ana@example.com", password="ultra_pass")
    user2 = User(id=2, name="Mile", surname="Stanislavov", email="mile@example.com", password="tekken")

    mock_app_service.list_participants.return_value = [user1, user2]

    with app.test_request_context(headers=auth_header):
        resource = ListParticipantsResource()
        response, status = resource.get(event_title="event_1", app_service=mock_app_service)

        assert status == 200
        # Check if the response serializes correctly
        assert isinstance(response, list)
        assert any(user["email"] == "ana@example.com" for user in response)
        assert any(user["email"] == "mile@example.com" for user in response)

    mock_app_service.list_participants.assert_called_once_with("event_1")

# --------------------------------------------------------------------------------
# The following test has been commented out until the model service is done

# def test_prompt_resource_forwards_prompt_to_model_service(app, mock_model_service, auth_header):
#     # 1) Arrange
#     prompt_text = "Just checking"
#     # Make sure the container lookup won’t blow up
#     from app import Container
#     from dependency_injector import providers
#     Container.model_service = providers.Object(None)
#
#     # 2) Act
#     with app.test_request_context(
#         f"/app/prompt?prompt={prompt_text}",
#         method="GET",
#         headers=auth_header,
#     ):
#         resource = PromptResource()
#         _, status = resource.get(model_service=mock_model_service)
#
#     # 3) Assert
#     assert status == 200
#     mock_model_service.query_prompt.assert_called_once_with(prompt_text)
# --------------------------------------------------------------------------------
