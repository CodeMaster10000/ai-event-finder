from dependency_injector.wiring import Provide, inject
from app.container import Container
from app.schemas.user_schema import UserSchema
from app.services.app_service import AppService
from app.services.model.model_service import ModelService
from app.util.logging_util import log_calls
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource, fields
from flask import request, abort

app_ns = Namespace("app", description="Event participation-related operations")
users_schema = UserSchema(many=True)


# Endpoint: POST and DELETE /app/<event_title>/participants/<user_email>
@app_ns.route("/<string:event_title>/participants/<string:user_email>")
@log_calls("app.routes")
class ParticipantResource(Resource):
    @inject
    @jwt_required()
    def post(
        self,
        event_title: str,
        user_email: str,
        app_service: AppService = Provide[Container.app_service],
    ):
        """Add a participant (by email in URL) to a specific event"""

        app_service.add_participant_to_event(event_title, user_email)
        return {"message": f"User '{user_email}' successfully added to event '{event_title}'"}, 201

    @inject
    @jwt_required()
    def delete(
        self,
        event_title: str,
        user_email: str,
        app_service: AppService = Provide[Container.app_service],
    ):
        """Remove a participant (by email in URL) from a specific event"""

        app_service.remove_participant_from_event(event_title, user_email)
        return {"message": f"User '{user_email}' removed from event '{event_title}'"}, 200

# Endpoint: GET /app/<event_title>/participants
@app_ns.route("/<string:event_title>/participants")
@log_calls("app.routes")
class ListParticipantsResource(Resource):
    @inject
    @jwt_required()
    def get(
        self,
        event_title: str,
        app_service: AppService = Provide[Container.app_service],
    ):
        """List all participants in an event"""

        participant_list = app_service.list_participants(event_title)
        return users_schema.dump(participant_list), 200


@app_ns.route("/prompt")
@log_calls("app.routes")
class PromptResource(Resource):
    @app_ns.param(
        "prompt",
        "The user's chat prompt",
        _in="query",
        required=True
    )
    @inject
    @jwt_required()
    async def get(
        self,
        model_service: ModelService = Provide[Container.model_service],
    ):
        """Accept a user prompt via query-string and return the model’s response"""
        user_prompt = request.args.get("prompt")
        if not user_prompt:
            abort(400, "'prompt' query parameter is required")

        # Await the async query
        response = await model_service.query_prompt(user_prompt)
        return {"response": response}, 200
