import csv
import os
from datetime import datetime
from itertools import cycle

from flask.cli import AppGroup
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.user import User
from app.models.event import Event
from app.services.embedding_service.local_embedding_service import LocalEmbeddingService
from app.constants import (
    DEFAULT_PASSWORD,
    DESCRIPTION_MAX_LENGTH, CATEGORY_MAX_LENGTH, TITLE_MAX_LENGTH, LOCATION_MAX_LENGTH
)
from app.error_handler.exceptions import (
    UserNotFoundException,
    DuplicateEmailException,
    UserSaveException,
    EventAlreadyExistsException,
    EventSaveException,
    EventDeleteException,
    UserDeleteException,
    EmbeddingServiceException,
    InvalidDateFormatException,
)

seed_cli = AppGroup("seed")

CSV_PATH = os.getenv("SEED_EVENTS_CSV", "data/preprocessed_events.csv")
USERS_COUNT = int(os.getenv("SEED_USERS_COUNT", "20"))
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_embedding_service = LocalEmbeddingService()


def _parse_datetime(date_string: str) -> datetime | None:
    try:
        return datetime.strptime((date_string or "").strip(), DEFAULT_DATE_FORMAT)
    except ValueError:
        raise InvalidDateFormatException(date_string, DEFAULT_DATE_FORMAT)


@seed_cli.command("users")
def seed_users():
    """Seeds fake user data."""

    for user_index in range(1, USERS_COUNT + 1):
        db.session.add(User(
            name=f"User{user_index}",
            surname="Demo",
            email=f"user{user_index}@example.com",
            password=DEFAULT_PASSWORD,
        ))
    try:
        db.session.commit()
        print(f"Created {USERS_COUNT} users.")
    except IntegrityError as integrity_error:
        db.session.rollback()
        raise DuplicateEmailException("<unknown>") from integrity_error
    except Exception as exception:
        db.session.rollback()
        raise UserSaveException(exception) from exception


@seed_cli.command("events")
def seed_events():
    """Load events from CSV, validate, embed, assign to users round-robin. No truncation."""
    users = User.query.order_by(User.id.asc()).all()
    if not users:
        raise UserNotFoundException("No users found. Run `flask seed users` first.")

    try:
        with open(CSV_PATH, "r", encoding="utf-8") as csv_file:
            csv_rows = list(csv.DictReader(csv_file))
    except FileNotFoundError:
        print(f"CSV not found: {CSV_PATH}")
        return

    if not csv_rows:
        print("CSV is empty. Nothing to insert.")
        return

    round_robin_users = cycle(users)
    events_created = 0
    duplicate_events = 0
    parse_errors = 0
    length_violations = 0
    embedding_errors = 0

    for row_index, csv_row in enumerate(csv_rows, start=1):
        title = (csv_row.get("name") or csv_row.get("title") or "").strip()
        description = (csv_row.get("description") or "").strip()
        location = (csv_row.get("location") or "").strip()
        category = (csv_row.get("category") or "").strip()

        try:
            event_datetime = _parse_datetime(csv_row.get("datetime") or "")
        except InvalidDateFormatException:
            parse_errors += 1
            continue

        # required fields
        if not title or not event_datetime:
            parse_errors += 1
            continue

        # hard length checks (no truncation)
        if (len(title) > TITLE_MAX_LENGTH or
                len(description) > DESCRIPTION_MAX_LENGTH or
                len(location) > LOCATION_MAX_LENGTH or
                len(category) > CATEGORY_MAX_LENGTH):
            print(f"[{row_index}] skipped: field exceeds max length")
            length_violations += 1
            continue

        event_organizer = next(round_robin_users)

        # idempotency: (organizer_id, title, datetime)
        with db.session.no_autoflush:
            if db.session.query(Event.id).filter_by(
                    title=title, organizer_id=event_organizer.id
            ).filter(Event.datetime == event_datetime).first():
                try:
                    raise EventAlreadyExistsException(event_name=title)
                except EventAlreadyExistsException:
                    duplicate_events += 1
                    continue

        # embedding
        try:
            event_embedding = _embedding_service.create_embedding(
                f"Title: {title}. Description: {description}. Category: {category}. Location: {location}"
            )
        except EmbeddingServiceException as embedding_exception:
            print(f"[{row_index}] embedding error: {embedding_exception}")
            embedding_errors += 1
            continue
        except Exception as unexpected_exception:
            print(f"[{row_index}] unexpected embedding error: {unexpected_exception}")
            embedding_errors += 1
            continue

        db.session.add(Event(
            title=title,
            description=description or "No description",
            location=location or "TBA",
            category=category or "General",
            datetime=event_datetime,
            organizer_id=event_organizer.id,
            embedding=event_embedding,
        ))
        events_created += 1

    # single final commit (160 rows is fine)
    try:
        db.session.commit()
    except Exception as commit_exception:
        db.session.rollback()
        raise EventSaveException(commit_exception) from commit_exception

    print("Seed events summary:")
    print(f"  created: {events_created}")
    print(f"  duplicates: {duplicate_events}")
    print(f"  parse errors (missing/invalid title/datetime): {parse_errors}")
    print(f"  length violations: {length_violations}")
    print(f"  embedding errors: {embedding_errors}")


@seed_cli.command("clean")
def clean_seed_data():
    """Delete all events then users (in that order)."""
    try:
        # delete children first due to FK constraints
        events_deleted = db.session.query(Event).delete(synchronize_session=False)
    except Exception as delete_events_exception:
        db.session.rollback()
        raise EventDeleteException(event_id=None,
                                   original_exception=delete_events_exception)

    try:
        users_deleted = db.session.query(User).delete(synchronize_session=False)
        db.session.commit()
        print(f"Clean complete: deleted {events_deleted} events, {users_deleted} users")
    except Exception as delete_users_exception:
        db.session.rollback()
        raise UserDeleteException(user_id=None, original_exception=delete_users_exception)