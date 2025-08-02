from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from app.models.event import Event

class EventService(ABC):
    @abstractmethod
    def get_by_id(self, event_id: int) -> Optional[Event]:
        """Retrieve an event by the event ID."""
        pass

    @abstractmethod
    def get_by_title(self, title: str) -> Optional[Event]:
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
    def get_by_organizer_id(self, organizer_id: int) -> List[Event]:
        """Retrieve events created by the organizer name and surname."""
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
    def save(self, event: Event) -> Event:
        """Create a new event or update an existing event."""
        pass

    @abstractmethod
    def update(self, event: Event) -> Event:
        """Update an existing event's data."""
        pass

    @abstractmethod
    def delete_by_id(self, event_id: int) -> None:
        """Delete an event by the event ID. Raise an error if not found."""
        pass

    @abstractmethod
    def delete_by_title(self, title: str) -> None:
        """Delete an event by the title. Raise an error if not found."""
        pass

    @abstractmethod
    def exists_by_id(self, event_id: int) -> bool:
        """Check whether an event exists by ID."""
        pass

    @abstractmethod
    def exists_by_title(self, title: str) -> bool:
        """Check whether an event exists by title."""
        pass

    @abstractmethod
    def exists_by_location(self, location: str) -> bool:
        """Check whether an event exists by location."""
        pass

    @abstractmethod
    def exists_by_category(self, category: str) -> bool:
        """Check whether an event exists by category."""
        pass