from typing import List
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.models.event import Event
from app.repositories.event_repository import EventRepository
from app.repositories.user_repository import UserRepository
from app.services.app_service import AppService
from app.util.validation_util import validate_user, validate_event
from app.util.user_util import return_not_found_by_email_message
from app.util.event_util import return_not_found_by_title_message
from app.error_handler.exceptions import UserNotInEventException, UserAlreadyInEventException, EventSaveException
from app.util.logging_util import log_calls
from psycopg2.errors import UniqueViolation

@log_calls("app.services")
class AppServiceImpl(AppService):
    """
    Orchestrates user–event interactions by delegating persistence
    to UserRepository and EventRepository.
    """
    def __init__(self, user_repo:UserRepository, event_repo:EventRepository):
        """
        :param user_repo: Used to lookup users by email
        :param event_repo: Used to lookup and persist events by title
        """
        self.user_repo = user_repo
        self.event_repo = event_repo

    def add_participant_to_event(self, event_title: str, user_email: str) -> None:
        """
        Add the user (user_email) to the event (event_title).
        Raises custom Exception if either entity is missing,
        Raises UserAlreadyInEvent if the user is already a participant.
        """
        event = self._get_event_and_validate(event_title=event_title)
        user = self._get_user_and_validate(user_email=user_email)

        if user in event.guests:
            raise UserAlreadyInEventException(user_email=user_email, event_title=event_title)

        try:
            event.guests.append(user)
            self.event_repo.save(event)
        except IntegrityError as e:
            # only convert UNIQUE constraint violations on the guest_list table
            if isinstance(e.orig, UniqueViolation):
                raise UserAlreadyInEventException(user_email, event_title)
            # something else went wrong—surface it as a save error
            raise EventSaveException(original_exception=e)

    def remove_participant_from_event(self, event_title: str, user_email: str) -> None:
        """
        Remove the user (user_email) from the event (event_title)
        Raises custom Exception if either entity is missing.
        Raises UserNotInEvent if user is not a participant.
        """
        event = self._get_event_and_validate(event_title=event_title)
        user = self._get_user_and_validate(user_email=user_email)

        if user not in event.guests:
            raise UserNotInEventException(user_email=user_email, event_title=event_title)
        event.guests.remove(user)
        self.event_repo.save(event)

    def list_participants(self, event_title: str) -> List[User]:
        """
        Returns a list of users participating in the event (event_title)
        Raises custom Exception if event is missing.
        """
        event = self._get_event_and_validate(event_title=event_title)
        return list(event.guests)

    # ----------- PRIVATE HELPERS ------------- #
    def _get_event_and_validate(self, event_title:str) -> Event:
        """
        Fetches an event by title and validates it.
        :param event_title:
        """
        event = self.event_repo.get_by_title(event_title)
        validate_event(event, return_not_found_by_title_message(event_title))
        return event

    def _get_user_and_validate(self, user_email:str) -> User:
        """
        Fetches a user by email and validates it.
        :param user_email:
        """
        user = self.user_repo.get_by_email(user_email)
        validate_user(user, return_not_found_by_email_message(user_email))
        return user

