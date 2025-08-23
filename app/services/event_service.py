from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from app.models.event import Event

class EventService(ABC):

    @abstractmethod
    def get_by_title(self, title: str) -> Event:
        """Retrieve an event by the title."""
        pass

    @abstractmethod
    def get_by_location(self, location: str) -> List[Event]:
        """Retrieve an event by the event location."""
        pass

    @abstractmethod
    def get_by_category(self, category: str) -> List[Event]:
        """Retrieve an event by the event category."""
        pass

    @abstractmethod
    def get_by_organizer(self, email)->List[Event]:
        pass

    @abstractmethod
    def get_by_date(self, date: datetime) -> List[Event]:
        """Check for events on a certain date."""
        pass

    @abstractmethod
    def get_all(self) -> List[Event]:
        """Retrieve a list of all events."""
        pass

    @abstractmethod
    def create(self, data: dict) -> Event:
        """Create a new event from validated payload."""
        pass

    @abstractmethod
    def update(self, title:str, patch:dict) -> Event:
        """Update an existing event's data."""
        pass


    @abstractmethod
    def delete_by_title(self, title: str) -> None:
        """Delete an event by the title. Raise an error if not found."""
        pass

