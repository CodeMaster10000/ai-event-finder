from app.extensions import db
from app.util.user_util import NAME_MAX_LENGTH,SURNAME_MAX_LENGTH,EMAIL_MAX_LENGTH,PASSWORD_MAX_LENGTH
from app.models.event import guest_list

class User(db.Model):
    """
    Represents a user in the database.

    Attributes:
        id (int): The id of the user. Used as the primary key.
        name (str): The name of the user. Max 50 characters.
        surname (str): The surname of the user. Max 50 characters.
        email (str): The email address of the user. Max 80 characters.
        password (str): The password of the user. Max 80 characters.
    """

    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(NAME_MAX_LENGTH), nullable=False)
    surname=db.Column(db.String(SURNAME_MAX_LENGTH), nullable=False)
    email = db.Column(db.String(EMAIL_MAX_LENGTH), nullable=False, unique=True)
    password=db.Column(db.String(PASSWORD_MAX_LENGTH), nullable=False)

    # MANY TO MANY
    events_attending = db.relationship(
        'Event',
        secondary=guest_list,
        back_populates='guests',
        lazy='dynamic'
    )
    # ONE TO MANY
    organized_events = db.relationship(
        'Event',
        back_populates='organizer',
        lazy='dynamic'
    )

    def __repr__(self):
        """
        Returns a readable string representation of the user.

        Returns:
            str: A string like '<User 1 - John Smith - john.smith@example.com>'.
        """
        return f"<User {self.id} - {self.name} {self.surname} - {self.email}>"

