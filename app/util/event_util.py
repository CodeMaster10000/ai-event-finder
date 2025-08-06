"""Event Entity Specific Variables"""
TITLE_MAX_LENGTH = 50
DESCRIPTION_MAX_LENGTH = 500
LOCATION_MAX_LENGTH = 50
CATEGORY_MAX_LENGTH = 50

from app.models.event import Event

def return_not_found_by_id_message(event_id) -> str:
    return f"Event not found with id {event_id}"
def return_not_found_by_title_message(title) -> str:
    return f"Event not found with title {title}"
def return_not_found_by_category_message(category) -> str:
    return f"Event not found with category {category}"
def return_not_found_by_location_message(location) -> str:
    return f"Event not found with location {location}"

def format_event(self, event: Event) -> str:
    """
    Format an Event object into a string prompt to send to the embedding model.

    Args:
        event (Event): Event object from the database.

    Returns:
        str: Formatted string representing the event.
    """
    fields = [
        event.title or "",
        event.description or "",
        event.location or "",
        event.category or "",
        event.datetime.isoformat() if event.datetime else "",
        str(event.organizer) if event.organizer else "",  # You could also use organizer.name or email
    ]

    return " | ".join(fields)
