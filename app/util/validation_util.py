from app.error_handler.exceptions import UserNotFoundException
from app.error_handler.exceptions import EventNotFoundException
from app.models.user import User
from app.models.event import Event
from typing import List


def validate_user(user: User, message: str) -> None:
    if not user:
        raise UserNotFoundException(message)

def validate_event(event: Event, message: str) -> None:
    if not event:
        raise EventNotFoundException(message)

def validate_event_list(events: List[Event], message: str) -> None:
    if not events:
        raise EventNotFoundException(message)
