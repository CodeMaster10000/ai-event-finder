from typing import List
from datetime import datetime
from app.models.event import Event
from app.repositories.event_repository import EventRepository
from app.repositories.user_repository import UserRepository
from app.services.event_service import EventService
from app.util.validation_util import validate_user, validate_event
from app.util.transaction_util import transactional, retry_conflicts
from app.extensions import db
from app.services.embedding_service.embedding_service import EmbeddingService
from app.util.format_event_util import format_event

from app.error_handler.exceptions import (
    EventNotFoundException,
    EventSaveException,
    EventDeleteException,
    EventAlreadyExistsException
)
from app.util.logging_util import log_calls

@log_calls("app.services")
class EventServiceImpl(EventService):
    def __init__(self, event_repository: EventRepository, user_repository: UserRepository, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.event_repository = event_repository
        self.user_repository = user_repository

    @transactional
    def get_by_title(self, title: str, session=None) -> Event:
        event = self.event_repository.get_by_title(title, session)
        validate_event(event, f"No event with title '{title}'")
        return event

    @transactional
    def get_by_location(self, location: str, session=None) -> List[Event]:
        return self.event_repository.get_by_location(location, session)

    @transactional
    def get_by_category(self, category: str, session=None) -> List[Event]:
        return self.event_repository.get_by_category(category, session)

    @transactional
    def get_by_organizer(self, email: str, session=None) -> List[Event]:
        organizer = self.user_repository.get_by_email(email, session)
        validate_user(organizer, f"No user found with email {email}")
        return self.event_repository.get_by_organizer_id(organizer.id, session)

    @transactional
    def get_by_date(self, date: datetime, session=None) -> List[Event]:
        return self.event_repository.get_by_date(date, session)

    @transactional
    def get_all(self, session=None) -> List[Event]:
        return self.event_repository.get_all(session)

    @retry_conflicts(max_retries=3, backoff_sec=0.1)
    @transactional
    def delete_by_title(self, title: str, session=None) -> None:
        event = self.event_repository.get_by_title(title, session)
        if not event:
            raise EventNotFoundException(f"Event with title '{title}' not found.")
        try:
            self.event_repository.delete_by_title(title, session)
        except Exception as e:
            raise EventDeleteException(original_exception=e)

    # TRANSACTIONAL - SPLIT INTO 2 TRANSACTIONS / @transactional helper method

    async def create(self, data: dict) -> Event:
        # 1) Ensure no duplicate title
        if self.event_repository.get_by_title(data['title'], db.session):
            # end the read txn and bail
            db.session.rollback()
            raise EventAlreadyExistsException(data['title'])

        # 2) Resolve organizer email → User
        email = data.get('organizer_email')
        organizer = self.user_repository.get_by_email(email, db.session)
        validate_user(organizer, f"No user found with email {email}")

        # 3) Build the Event model, dropping organizer_email
        payload = {k: v for k, v in data.items() if k != 'organizer_email'}
        event = Event(**payload, organizer_id=organizer.id)

        # close read-only txn before external I/O
        formatted = format_event(event)
        db.session.rollback()

        # External call: await async embedding
        event.embedding = await self.embedding_service.create_embedding(formatted)

        # 4) Persist it
        try:
            saved = self._persist(event, recheck_title=True, title_for_recheck=data['title'])
            return saved
        except EventAlreadyExistsException:
            raise
        except Exception as e:
            raise EventSaveException(original_exception=e)


    async def update(self, title: str, patch: dict) -> Event:
        """
        Update an existing Event by its unique title.
        The title itself cannot be changed.
        """
        # 1. Read-only fetch existing event
        existing_event = self.event_repository.get_by_title(title, db.session)
        if not existing_event:
            raise EventNotFoundException(f"Event with title '{title}' not found.")

        # 2. Build temporary event object for formatting + embedding
        temp_data = {col: getattr(existing_event, col) for col in existing_event.__table__.columns.keys()}
        temp_data.update(patch)  # apply patch fields
        temp_event = Event(**temp_data)

        # 3. End read-only transaction
        db.session.rollback()

        # 4. Create embedding asynchronously
        temp_event.embedding = await self.embedding_service.create_embedding(format_event(temp_event))

        # 5. Transactional write to persist patch + embedding
        @transactional
        def _write_update(session=None):
            # re-fetch to attach to current transactional session
            event_to_update = self.event_repository.get_by_title(title, session)
            if not event_to_update:
                raise EventNotFoundException(f"Event with title '{title}' no longer exists.")

            # apply patch fields
            for key, value in patch.items():
                setattr(event_to_update, key, value)
            # apply new embedding
            event_to_update.embedding = temp_event.embedding

            # flush changes
            session.flush()
            return event_to_update

        return _write_update()



    @retry_conflicts(max_retries=3, backoff_sec=0.1)
    @transactional
    def _persist(self, event: Event, *, session=None, recheck_title: bool = False,
                 title_for_recheck: str | None = None) -> Event:
        # Optional TOCTOU recheck (used by create)
        if recheck_title and title_for_recheck:
            with session.no_autoflush:
                found = self.event_repository.get_by_title(title_for_recheck, session)
                # Only a conflict if it's a different event
                if found and getattr(found, "id", None) != getattr(event, "id", None):
                    raise EventAlreadyExistsException(title_for_recheck)

        # Now save the event
        return self.event_repository.save(event, session)
