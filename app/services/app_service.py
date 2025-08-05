from abc import ABC, abstractmethod
from typing import List
from app.models.user import User

class AppService(ABC):
    @abstractmethod
    def add_participant_to_event(self, event_title: str, user_email: str) -> None:
        """
        Add a participant (by user_email) to the event (by event_title).
        """
        pass

    @abstractmethod
    def remove_participant_from_event(self, event_title: str, user_email: str) -> None:
        """
        Remove a participant (by user_email) from the event (by event_title).
        """
        pass

    @abstractmethod
    def list_participants(self, event_title: str) -> List[User]:
        """
        Retrieve a list of all participants for the given event_title.
        """
        pass
