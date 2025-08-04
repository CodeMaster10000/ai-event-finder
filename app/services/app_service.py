from abc import ABC, abstractmethod
from typing import List
from app.models.user import User

class AppService(ABC):
    @abstractmethod
    def add_participant_to_event(self, event_id: int, user_id: int) -> None:
        """
        Add a participant (by user_id) to the event (by event_id).
        """
        pass

    @abstractmethod
    def remove_participant_from_event(self, event_id: int, user_id: int) -> None:
        """
        Remove a participant (by user_id) from the event (by event_id).
        """
        pass

    @abstractmethod
    def list_participants(self, event_id: int) -> List[User]:
        """
        Retrieve a list of all participants for the given event.
        """
        pass
