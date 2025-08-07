from app.models.event import Event
def format_event(event: Event) -> str:
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
