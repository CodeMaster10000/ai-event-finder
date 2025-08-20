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
from sqlalchemy import inspect
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
        event = self.event_repository.get_by_title(title, db.session)
        validate_event(event, f"No event with title '{title}")
        return event

    def get_by_location(self, location: str) -> List[Event]:
        return self.event_repository.get_by_location(location, db.session)

    def get_by_category(self, category: str) -> List[Event]:
        return self.event_repository.get_by_category(category, db.session)

    def get_by_organizer(self, email: str) -> List[Event]:
        organizer = self.user_repository.get_by_email(email, db.session)
        validate_user(organizer, f"No user found with email {email}")
        return self.event_repository.get_by_organizer_id(organizer.id,db.session)

    def get_by_date(self, date: datetime) -> List[Event]:
        return self.event_repository.get_by_date(date,db.session)

    def get_all(self) -> List[Event]:
        return self.event_repository.get_all(db.session)

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

    async def update(self, event: Event) -> Event:
        # Capture the new title separately for early uniqueness check
        new_title = event.title

        # Avoid autoflush while we run read-side checks
        with db.session.no_autoflush:
            existing_event = self.event_repository.get_by_id(event.id, db.session)
            conflict = self.event_repository.get_by_title(new_title, db.session)

        if conflict is not None and existing_event is not None and conflict.id != existing_event.id:
            raise EventAlreadyExistsException(conflict.title)
        if not existing_event:
            raise EventNotFoundException("Event not found in the database.")

        # ---- Build a patch of user changes BEFORE rollback ----
        state = inspect(event)
        pending_changes = {}
        for attr in state.attrs:
            # keep only attributes the user actually changed
            if attr.history.has_changes():
                key = attr.key
                # we'll set embedding explicitly after the external call
                if key == "embedding":
                    continue
                pending_changes[key] = getattr(event, key)

        # Prepare the formatted payload from the edited state
        formatted = format_event(event)

        # End the read-only transaction before the external I/O
        db.session.rollback()

        # External call (await async embedding)
        event.embedding = await self.embedding_service.create_embedding(formatted)

        # Re-apply the user's pending changes that rollback may have expired
        for key, value in pending_changes.items():
            setattr(event, key, value)

        try:
            # Re-check title inside the short write txn (TOCTOU guard) and persist
            updated = self._persist(event, recheck_title=True, title_for_recheck=event.title)
            return updated
        except EventAlreadyExistsException:
            # bubble up domain conflict unchanged
            raise
        except Exception as e:
            raise EventSaveException(original_exception=e)

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
