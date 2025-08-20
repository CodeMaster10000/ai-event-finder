import logging
from flask_restx import Namespace, Resource, fields
from flask import request, abort
from dependency_injector.wiring import inject, Provide
from app.container import Container
from app.services.event_service import EventService
from app.schemas.event_schema import CreateEventSchema, EventSchema
from app.util.logging_util import log_calls
from datetime import datetime
from flask_jwt_extended import jwt_required

# Namespace for event operations; all routes under '/events'
event_ns = Namespace("events", description="Event based operations")

# Instantiate Marshmallow schemas for input validation and serialization
create_event_schema = CreateEventSchema()  # Validates incoming POST data
event_schema = EventSchema()               # Serializes a single Event object
events_schema = EventSchema(many=True)     # Serializes a list of Event objects


@log_calls("app.routes")  # Custom decorator for logging entry/exit of methods
@event_ns.route("")       # Root endpoint for events (e.g., GET /events, POST /events)
class EventBaseResource(Resource):
    @inject  # Inject EventService from DI container
    @jwt_required()
    def get(self,
            event_service: EventService = Provide[Container.event_service]):
        """Get all events"""
        events = event_service.get_all()                  # Fetch list of Event models
        return events_schema.dump(events), 200            # Return serialized list with HTTP 200

    # Define Swagger model for input payload documentation
    event_create_input = event_ns.model('event_create_input', {
        'title':           fields.String(required=True),  # Event title must be provided
        'description':     fields.String(required=True),  # Event description
        'datetime':        fields.String(required=True),  # Date/time in specific format
        'location':        fields.String(required=True),  # Location string
        'category':        fields.String(required=True),  # Category string
        'organizer_email': fields.String(required=True),  # Email of user organizing this event
    })

    @event_ns.expect(event_create_input)
    @inject
    @jwt_required()
    async def post(self,
             event_service: EventService = Provide[Container.event_service]):
        """Create a new event"""
        # 1. Validate & deserialize the JSON (still requires organizer_email)
        data = create_event_schema.load(request.get_json())

        # 2. Delegate everything (including email lookup) to the service
        saved = await event_service.create(data)

        # 3. Serialize and return the newly created event
        return event_schema.dump(saved), 201


@log_calls("app.routes")
@event_ns.route('/title/<string:title>')  # Endpoint for operations by title
class EventByTitleResource(Resource):
    @inject
    @jwt_required()
    def get(self,
            title: str,
            event_service: EventService = Provide[Container.event_service]):
        """Get an event by title"""
        event = event_service.get_by_title(title)
        return event_schema.dump(event), 200

    @inject
    @jwt_required()
    def delete(self,
               title: str,
               event_service: EventService = Provide[Container.event_service]):
        """Delete an event by title"""
        event = event_service.get_by_title(title)
        if not event:
            abort(404, description=f"Event with title {title} not found")
        event_service.delete_by_title(title)
        return '', 204  # No content on successful delete


@log_calls("app.routes")
@event_ns.route('/location/<string:location>')  # Endpoint to query by location
class EventsByLocationResource(Resource):
    @inject
    @jwt_required()
    def get(self,
            location: str,
            event_service: EventService = Provide[Container.event_service]):
        """Get events by location"""
        events = event_service.get_by_location(location)
        return events_schema.dump(events), 200


@log_calls("app.routes")
@event_ns.route('/category/<string:category>')  # Endpoint to query by category
class EventsByCategoryResource(Resource):
    @inject
    @jwt_required()
    def get(self,
            category: str,
            event_service: EventService = Provide[Container.event_service]):
        """Get events by category"""
        events = event_service.get_by_category(category)
        return events_schema.dump(events), 200


@log_calls("app.routes")
@event_ns.route('/organizer/<string:email>')  # Endpoint to query by organizer email
class EventsByOrganizerResource(Resource):
    @inject
    @jwt_required()
    def get(self,
            email: str,
            event_service: EventService = Provide[Container.event_service]):
        """Get events by organizer email"""
        events = event_service.get_by_organizer(email)
        return events_schema.dump(events), 200


@log_calls("app.routes")
@event_ns.route('/date/<string:date_str>')  # Endpoint to query by date string
class EventsByDateResource(Resource):
    @inject
    @jwt_required()
    def get(self,
            date_str: str,
            event_service: EventService = Provide[Container.event_service]):
        """Get events by date (YYYY-MM-DD)"""
        try:
            # Parse incoming date string to datetime.date
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            abort(400, description="Date must be in 'YYYY-MM-DD' format")
        events = event_service.get_by_date(date_obj)
        return events_schema.dump(events), 200
