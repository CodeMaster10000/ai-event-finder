from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from app.models.event import Event


class EventRepository(ABC):
    """
    Abstract base class defining the contract for an Event repository.
    Provides methods for querying, saving, deleting, and checking existence of Event entities.
    """

    def __init__(self, session):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session (Session): The SQLAlchemy session to use for database operations.

        Note:
            Concrete implementations should pass the session to the base constructor
            so it can be shared or reused consistently.
        """
        self.session = session

    # ------------------------
    # Retrieval Methods
    # ------------------------

    @abstractmethod
    def get_all(self) -> List[Event]:
        """
        Retrieve all events stored in the repository.

        Returns:
            List[Event]: A list of all events.
        """
        pass

    @abstractmethod
    def get_by_id(self, event_id: int) -> Optional[Event]:
        """
        Retrieve a single event by its unique ID.

        Args:
            event_id (int): The ID of the event.

        Returns:
            Optional[Event]: The event with the specified ID, or None if not found.
        """
        pass

    @abstractmethod
    def get_by_title(self, title: str) -> Optional[Event]:
        """
        Retrieve all events that match a given title.

        Args:
            title (str): The title to search for.

        Returns:
            List[Event]: A list of events with the given title.
        """
        pass

    @abstractmethod
    def get_by_organizer_id(self, organizer_id: int) -> List[Event]:
        """
        Retrieve all events organized by a specific user.

        Args:
            organizer_id (int): The ID of the organizer.

        Returns:
            List[Event]: A list of events organized by the user.
        """
        pass

    @abstractmethod
    def get_by_date(self, date: datetime) -> List[Event]:
        """
        Retrieve all events scheduled on a specific date.

        Args:
            date (datetime): The date to filter by.

        Returns:
            List[Event]: A list of events held on the given date.
        """
        pass

    @abstractmethod
    def get_by_location(self, location: str) -> List[Event]:
        """
        Retrieve all events held at a specific location.

        Args:
            location (str): The location to search for.

        Returns:
            List[Event]: A list of events held at the location.
        """
        pass

    @abstractmethod
    def get_by_category(self, category: str) -> List[Event]:
        """
        Retrieve all events in a given category.

        Args:
            category (str): The category to filter by.

        Returns:
            List[Event]: A list of events in the category.
        """
        pass

    # ------------------------
    # Deletion Methods
    # ------------------------

    @abstractmethod
    def delete_by_id(self, event_id: int) -> None:
        """
        Delete an event from the repository by its ID.

        Args:
            event_id (int): The ID of the event to delete.
        """
        pass

    @abstractmethod
    def delete_by_title(self, title: str) -> None:
        """
        Delete all events with the specified title from the repository.

        Args:
            title (str): The title of the events to delete.

        Note:
            This method assumes that multiple events can share the same title.
            If only unique titles are expected in your domain model, this should delete one or raise an error.
        """
        pass

    # ------------------------
    # Save Method
    # ------------------------

    @abstractmethod
    def save(self, event: Event) -> Event:
        """
        Save or update an event in the repository.

        If the event already exists (e.g., based on its ID), it should be updated.
        Otherwise, a new event should be created.

        Args:
            event (Event): The event to save or update.

        Returns:
            Event: The saved or updated event instance.
        """
        pass

    # ------------------------
    # Existence Checks
    # ------------------------

    @abstractmethod
    def exists_by_id(self, event_id: int) -> bool:
        """
        Check whether an event with the given ID exists.

        Args:
            event_id (int): The ID to check.

        Returns:
            bool: True if an event with the ID exists, False otherwise.
        """
        pass

    @abstractmethod
    def exists_by_title(self, title: str) -> bool:
        """
        Check whether any events exist with the given title.

        Args:
            title (str): The title to check.

        Returns:
            bool: True if one or more events with the title exist, False otherwise.
        """
        pass

    @abstractmethod
    def exists_by_location(self, location: str) -> bool:
        """
        Check whether any events exist at the given location.

        Args:
            location (str): The location to check.

        Returns:
            bool: True if events are scheduled at the location, False otherwise.
        """
        pass

    @abstractmethod
    def exists_by_category(self, category: str) -> bool:
        """
        Check whether any events exist in the specified category.

        Args:
            category (str): The category to check.

        Returns:
            bool: True if events exist in the category, False otherwise.
        """
        pass

    @abstractmethod
    def exists_by_date(self, date: datetime) -> bool:
        """
        Check whether any events are held on the given date.

        Args:
            date (datetime): The date to check.

        Returns:
            bool: True if one or more events are held on that date, False otherwise.
        """
        pass
