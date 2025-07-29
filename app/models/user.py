from app.extensions import db

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
    name=db.Column(db.String(50), nullable=False)
    surname=db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(80), nullable=False, unique=True)
    password=db.Column(db.String(80), nullable=False)

    def __repr__(self):
        """
        Returns a readable string representation of the user.

        Returns:
            str: A string like '<User 1 - John Smith - john.smith@example.com>'.
        """
        return f"<User {self.id} - {self.name} {self.surname} - {self.email}>"

