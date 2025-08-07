import os
from datetime import datetime

from pgvector.sqlalchemy import Vector

from app.configuration.config import Config
from app.extensions import db
from app.constants import (
    TITLE_MAX_LENGTH,
    DESCRIPTION_MAX_LENGTH,
    LOCATION_MAX_LENGTH,
    CATEGORY_MAX_LENGTH,
)

# MANY-TO-MANY association table for guest lists
guest_list = db.Table(
    'guest_list',
    db.Column('event_id', db.Integer, db.ForeignKey('events.id'), primary_key=True),
    db.Column('user_id',  db.Integer, db.ForeignKey('user.id'),   primary_key=True),
)

class Event(db.Model):
    """
    Represents an event in the database.

    Attributes:
        id (int):                  Primary key.
        title (str):               Title (max length = TITLE_MAX_LENGTH).
        datetime (datetime):       When the event takes place.
        description (str):         Description (max length = DESCRIPTION_MAX_LENGTH).
        embedding (vector):        Vector embedding (dim = Config.VECTOR_DIM).
        organizer_id (int):        FK to User who organized.
        organizer (User):          Relationship to the organizer.
        location (str):            Location (max length = LOCATION_MAX_LENGTH).
        category (str):            Category (max length = CATEGORY_MAX_LENGTH).
        guests (List[User]):       Users invited to the event.
    """
    __tablename__ = 'events'

    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(TITLE_MAX_LENGTH), nullable=False)
    datetime     = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description  = db.Column(db.String(DESCRIPTION_MAX_LENGTH), nullable=True)
    embedding    = db.Column(Vector(Config.VECTOR_DIM), nullable=True)

    # ONE-TO-MANY: organizer
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    organizer    = db.relationship(
        'User',
        back_populates='organized_events',
        lazy='joined',
    )

    location     = db.Column(db.String(LOCATION_MAX_LENGTH), nullable=True)
    category     = db.Column(db.String(CATEGORY_MAX_LENGTH), nullable=True)

    # MANY-TO-MANY: guests
    guests = db.relationship(
        'User',
        secondary=guest_list,
        back_populates='events_attending',
        lazy='dynamic',
    )

    def __repr__(self):
        return f"<Event {self.id} – {self.title} @ {self.datetime.isoformat()}>"
