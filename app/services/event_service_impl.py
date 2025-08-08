from typing import List
from datetime import datetime
from app.models.event import Event
from app.repositories.event_repository import EventRepository
from app.repositories.user_repository import UserRepository
from app.services.event_service import EventService
from app.util.validation_util import validate_user, validate_event
from app.services.embedding_service.embedding_service import EmbeddingService
from app.util.format_event_util import format_event

from app.error_handler.exceptions import (
    EventNotFoundException,
    EventSaveException,
    EventDeleteException,
    EventAlreadyExistsException
)

class EventServiceImpl(EventService):
    def __init__(self, event_repository: EventRepository, user_repository: UserRepository, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.event_repository = event_repository
        self.user_repository = user_repository

    def get_by_title(self, title: str) -> Event:
        event = self.event_repository.get_by_title(title)
        validate_event(event, f"No event with title '{title}")
        return event

    def get_by_location(self, location: str) -> List[Event]:
        return self.event_repository.get_by_location(location)

    def get_by_category(self, category: str) -> List[Event]:
        return self.event_repository.get_by_category(category)

    def get_by_organizer(self, email: str) -> List[Event]:
        organizer = self.user_repository.get_by_email(email)
        validate_user(organizer, f"No user found with email {email}")
        return self.event_repository.get_by_organizer_id(organizer.id)

    def get_by_date(self, date: datetime) -> List[Event]:
        return self.event_repository.get_by_date(date)

    def get_all(self) -> List[Event]:
        return self.event_repository.get_all()

    def delete_by_title(self, title: str) -> None:
        event = self.event_repository.get_by_title(title)
        if not event:
            raise EventNotFoundException(f"Event with title '{title}' not found.")
        try:
            self.event_repository.delete_by_title(title)
        except Exception as e:
            raise EventDeleteException(original_exception=e)

    def create(self, data: dict) -> Event:
        # 1) Ensure no duplicate title
        if self.event_repository.get_by_title(data['title']):
            raise EventAlreadyExistsException(data['title'])

        # 2) Resolve organizer email → User
        email = data.get('organizer_email')
        organizer = self.user_repository.get_by_email(email)
        validate_user(organizer, f"No user found with email {email}")

        # 3) Build the Event model, dropping organizer_email
        payload = {k: v for k, v in data.items() if k != 'organizer_email'}
        event = Event(**payload, organizer_id=organizer.id)

        formatted = format_event(event)
        event.embedding = self.embedding_service.create_embedding(formatted)

        # 4) Persist it
        try:
            saved = (self.event_repository.save(event))
            return saved
        except Exception as e:
            raise EventSaveException(original_exception=e)

    def update(self, event: Event) -> Event:
        existing_event = self.event_repository.get_by_id(event.id)
        conflict = self.event_repository.get_by_title(event.title)

        if conflict is not None and existing_event is not None and conflict.id != existing_event.id:
            raise EventAlreadyExistsException(conflict.title)

        if not existing_event:
            raise EventNotFoundException("Event not found in the database.")

        formatted = format_event(event)
        event.embedding = self.embedding_service.create_embedding(formatted)

        try:
            updated = self.event_repository.save(event)
            return updated
        except Exception as e:
            raise EventSaveException(original_exception=e)