from app.extensions import db
from app.models.user import User
from app.util.event_util import TITLE_MAX_LENGTH, DESCRIPTION_MAX_LENGTH, LOCATION_MAX_LENGTH, CATEGORY_MAX_LENGTH


# MANY TO MANY -> association table, actual join table in db schema
# used by SQLAlchemy in SQL JOINs
guest_list = db.Table(
    'guest_list',
    db.Column('event_id', db.Integer, db.ForeignKey('events.id'), primary_key=True),
    db.Column('user_id',  db.Integer, db.ForeignKey('user.id'),   primary_key=True)
)

class Event(db.Model):
    """
    Represents an event in the database.

    Attributes:
        id (int):          The id of the event. Primary key.
        title (str):       The title of the event. Max 100 characters.
        datetime (datetime): When the event takes place.
        description (str): Textual description of the event.
        organizer_id (int): Foreign key to the User organizing the event.
        organizer (User):  Relationship to the User who organized the event.
        location (str):    Location of the event. Max 100 characters.
        guests (List[User]): Users invited to the event.
        category (str):    Category of the event. Max 50 characters.
    """

    id           = db.Column(db.Integer,   primary_key=True)
    title        = db.Column(db.String(TITLE_MAX_LENGTH), nullable=False)
    datetime     = db.Column(db.DateTime,   nullable=False)
    description  = db.Column(db.Text(DESCRIPTION_MAX_LENGTH),       nullable=True)

    # ONE TO MANY
    organizer_id = db.Column(db.Integer,    db.ForeignKey('user.id'), nullable=False)
    organizer = db.relationship(
        'User',
        back_populates='organized_events',
        lazy='joined'
    )

    location     = db.Column(db.String(LOCATION_MAX_LENGTH), nullable=True)
    category     = db.Column(db.String(CATEGORY_MAX_LENGTH),  nullable=True)

    # MANY TO MANY -> a relationship
    # query, ORM
    guests = db.relationship(
        'User',
        secondary=guest_list,
        back_populates='events_attending',
        lazy='dynamic'
    )

    def __repr__(self):
        return f"<Event {self.id} – {self.title} @ {self.datetime}>"
