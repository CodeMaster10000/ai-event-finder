from app.extensions import db
from app.util.user_util import NAME_MAX_LENGTH, SURNAME_MAX_LENGTH, EMAIL_MAX_LENGTH, PASSWORD_MAX_LENGTH
from app.models.event import guest_list

class User(db.Model):
    """
    Represents a user in the database.

    Attributes:
        id (int):                    Primary key.
        name (str):                  User's first name (max length = NAME_MAX_LENGTH).
        surname (str):               User's surname (max length = SURNAME_MAX_LENGTH).
        email (str):                 User's email address (max length = EMAIL_MAX_LENGTH).
        password (str):              Hashed password (max length = PASSWORD_MAX_LENGTH).
        version (int):               Optimistic lock version counter (auto-incremented on update).
        events_attending (List[Event]): Events this user is invited to.
        organized_events (List[Event]): Events this user has organized.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(NAME_MAX_LENGTH), nullable=False)
    surname = db.Column(db.String(SURNAME_MAX_LENGTH), nullable=False)
    email = db.Column(db.String(EMAIL_MAX_LENGTH), nullable=False, unique=True, index=True)
    password = db.Column(db.String(PASSWORD_MAX_LENGTH), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)

    # MANY-TO-MANY: events this user is attending
    events_attending = db.relationship(
        'Event',
        secondary=guest_list,
        back_populates='guests',
        lazy='dynamic'
    )
    # ONE-TO-MANY: events this user has organized
    organized_events = db.relationship(
        'Event',
        back_populates='organizer',
        lazy='dynamic'
    )

    __mapper_args__ = {
        "version_id_col": version,
    }

    def __repr__(self):
        """
        Returns a readable string representation of the user.

        Returns:
            str: A string like '<User 1 - John Smith - john.smith@example.com>'.
        """
        return f"<User {self.id} - {self.name} {self.surname} - {self.email}>"