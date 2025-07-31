from app.error_handler.exceptions import UserNotFoundException
from app.models.user import User


def validate_user(user: User, *, user_id=None, email=None, name=None):
    if not user:
        raise UserNotFoundException(user_id=user_id, email=email, name=name)
