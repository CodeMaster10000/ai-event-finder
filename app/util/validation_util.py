from app.error_handler.exceptions import UserNotFoundException
from app.models.user import User


def validate_user(user: User, message: str) -> None:
    if not user:
        raise UserNotFoundException(message)
