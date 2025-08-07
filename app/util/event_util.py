# app/util/event_util.py

"""Event-Entity helper functions"""

from app.constants import TITLE_MAX_LENGTH, DESCRIPTION_MAX_LENGTH, LOCATION_MAX_LENGTH, CATEGORY_MAX_LENGTH
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.event import Event


def return_not_found_by_id_message(event_id) -> str:
    return f"Event not found with id {event_id}"

def return_not_found_by_title_message(title) -> str:
    return f"Event not found with title {title}"

def return_not_found_by_category_message(category) -> str:
    return f"Event not found with category {category}"

def return_not_found_by_location_message(location) -> str:
    return f"Event not found with location {location}"


def format_event(event: "Event") -> str:
    """
    Format an Event object into a string prompt to send to the embedding model.
    """
    # local import so we only load Event at call time
    from app.models.event import Event

    fields = [
        event.title or "",
        event.description or "",
        event.location or "",
        event.category or "",
        event.datetime.isoformat() if event.datetime else "",
        str(event.organizer) if event.organizer else "",
    ]
    return " | ".join(fields)
