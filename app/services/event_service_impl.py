from typing import List, Optional
from datetime import datetime

from app.models.event import Event
from app.repositories.event_repository import EventRepository
from app.services.event_service import EventService
from app.util.validation_util import validate_event, validate_event_list
from app.util.event_util import *

from app.error_handler.exceptions import (
    EventNotFoundException,
    EventSaveException,
    EventDeleteException,
    EventAlreadyExistsException
)

class EventServiceImpl(EventService):
    def __init__(self, event_repository: EventRepository):
        self.event_repository = event_repository

    def delete_by_title(self, title: str) -> None:
        try:
            self.event_repository.delete_by_title(title)
        except Exception as e:
            raise EventDeleteException(original_exception=e)

    def get_by_id(self, event_id: int) -> Optional[Event]:
        return self.event_repository.get_by_id(event_id)

    def get_by_title(self, title: str) -> Optional[Event]:
        return self.event_repository.get_by_title(title)

    def get_by_location(self, location: str) -> List[Event]:
        return self.event_repository.get_by_location(location)

    def get_by_category(self, category: str) -> List[Event]:
        return self.event_repository.get_by_category(category)

    def get_by_organizer_id(self, organizer_id: int) -> List[Event]:
        return self.event_repository.get_by_organizer_id(organizer_id)

    def get_by_date(self, date: datetime) -> List[Event]:
        return self.event_repository.get_by_date(date)

    def get_all(self) -> List[Event]:
        return self.event_repository.get_all()

    def save(self, event: Event) -> Event:
        if self.event_repository.get_by_title(event.title):
            raise EventAlreadyExistsException(event.title)
        try:
            return self.event_repository.save(event)
        except Exception as e:
            raise EventSaveException(original_exception=e)

    def update(self, event: Event) -> Event:
        existing_event = self.event_repository.get_by_id(event.id)
        conflict = self.event_repository.get_by_title(event.title)

        if conflict is not None and existing_event is not None and conflict.id != existing_event.id:
            raise EventAlreadyExistsException(conflict.title)

        if not existing_event:
            raise EventNotFoundException(f"Event not found in the database.")

        try:
            return self.event_repository.save(event)
        except Exception as e:
            raise EventSaveException(original_exception=e)

    def delete_by_id(self, event_id: int) -> None:
        event = self.event_repository.get_by_id(event_id)
        validate_event(event, return_not_found_by_id_message(event_id))
        try:
            self.event_repository.delete_by_id(event_id)
        except Exception as e:
            raise EventDeleteException(event_id=event_id, original_exception=e)


    def exists_by_id(self, event_id: int) -> bool:
        event = self.event_repository.get_by_id(event_id)
        validate_event(event, return_not_found_by_id_message(event_id))
        return True

    def exists_by_title(self, title: str) -> bool:
        event = self.event_repository.get_by_title(title)
        validate_event(event, return_not_found_by_title_message(title))
        return True

    def exists_by_location(self, location: str) -> bool:
        events = self.event_repository.get_by_location(location)
        validate_event_list(events, return_not_found_by_location_message(location))
        return True

    def exists_by_category(self, category: str) -> bool:
        events = self.event_repository.get_by_category(category)
        validate_event_list(events, return_not_found_by_category_message(category))
        return True