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
from app.util.transaction_util import transactional, retry_conflicts
from app.error_handler.exceptions import UserNotInEventException, UserAlreadyInEventException, EventSaveException
from app.util.logging_util import log_calls
from psycopg2.errors import UniqueViolation
from app.extensions import db
from sqlalchemy.orm import Session

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

    @retry_conflicts(max_retries=3, backoff_sec=0.1)
    @transactional
    def add_participant_to_event(self, event_title: str, user_email: str, session=None) -> None:
        """
        Add the user (user_email) to the event (event_title).

        • Uses optimistic-locking on the request-scoped session.
        • Retries up to 3 times on version conflicts.
        • Converts duplicate-invite IntegrityErrors into UserAlreadyInEventException.
        """
        # 1) Load & validate
        event = self._get_event_and_validate(event_title, session)
        user = self._get_user_and_validate(user_email, session)

        # 2) Guard against an obvious double-invite
        if user in event.guests:
            raise UserAlreadyInEventException(user_email=user_email,
                                              event_title=event_title)

        # 3) Append + save inside one atomic transaction
        try:
            event.guests.append(user)
            self.event_repo.save(event, session)
        except IntegrityError as e:
            # Unique PK violation on the guest_list join => double-invite
            if isinstance(e.orig, UniqueViolation):
                raise UserAlreadyInEventException(user_email=user_email,
                                                  event_title=event_title)
            # Any other DB problem: wrap as a save error
            raise EventSaveException(original_exception=e)

    @retry_conflicts(max_retries=3, backoff_sec=0.1)
    @transactional
    def remove_participant_from_event(self, event_title: str, user_email: str, session=None) -> None:
        """
        Remove the user (user_email) from the event (event_title)
        Raises custom Exception if either entity is missing.
        Raises UserNotInEvent if user is not a participant.
        """
        event = self._get_event_and_validate(event_title=event_title, session=session)
        user = self._get_user_and_validate(user_email=user_email, session=session)

        if user not in event.guests:
            raise UserNotInEventException(user_email=user_email, event_title=event_title)
        event.guests.remove(user)
        self.event_repo.save(event, session)

    def list_participants(self, event_title: str) -> List[User]:
        """
        Returns a list of users participating in the event (event_title)
        Raises custom Exception if event is missing.
        """
        event = self._get_event_and_validate(event_title=event_title, session=db.session)
        return list(event.guests)

    # ----------- PRIVATE HELPERS ------------- #
    def _get_event_and_validate(self, event_title:str, session:Session) -> Event:
        """
        Fetches an event by title and validates it.
        :param event_title:
        """
        event = self.event_repo.get_by_title(event_title, session)
        validate_event(event, return_not_found_by_title_message(event_title))
        return event

    def _get_user_and_validate(self, user_email:str, session:Session) -> User:
        """
        Fetches a user by email and validates it.
        :param user_email:
        """
        user = self.user_repo.get_by_email(user_email, session)
        validate_user(user, return_not_found_by_email_message(user_email))
        return user

