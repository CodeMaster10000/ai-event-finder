from datetime import datetime, UTC
from pgvector.sqlalchemy import Vector

from app.configuration.config import Config
from app.extensions import db
from app.constants import (
    TITLE_MAX_LENGTH,
    DESCRIPTION_MAX_LENGTH,
    LOCATION_MAX_LENGTH,
    CATEGORY_MAX_LENGTH,
)

guest_list = db.Table(
    'guest_list',
    db.Column('event_id', db.Integer, db.ForeignKey('events.id'), primary_key=True),
    db.Column('user_id',  db.Integer, db.ForeignKey('user.id'),   primary_key=True),
)

class Event(db.Model):
    """Event with a single unified 1024-dim embedding column for semantic search."""
    __tablename__ = 'events'

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(TITLE_MAX_LENGTH), nullable=False)
    datetime    = db.Column(db.DateTime, nullable=False, default=datetime.now(UTC))
    description = db.Column(db.String(DESCRIPTION_MAX_LENGTH), nullable=True)

    # Unified 1024-d vector for OpenAI and Ollama embeddings
    embedding = db.Column(Vector(Config.UNIFIED_VECTOR_DIM), nullable=True)

    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    organizer    = db.relationship('User', back_populates='organized_events', lazy='joined')

    location     = db.Column(db.String(LOCATION_MAX_LENGTH), nullable=True)
    category     = db.Column(db.String(CATEGORY_MAX_LENGTH), nullable=True)

    guests = db.relationship('User', secondary=guest_list, back_populates='events_attending', lazy='dynamic')

    def __repr__(self):
        return f"<Event {self.id} – {self.title} @ {self.datetime.isoformat()}>"
