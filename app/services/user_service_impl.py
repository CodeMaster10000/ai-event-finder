from typing import List
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService
from app.util.user_util import return_not_found_by_name_message, return_not_found_by_email_message, \
    return_not_found_by_id_message
from app.util.validation_util import validate_user

from app.error_handler.exceptions import (
    DuplicateEmailException,
    UserSaveException,
    UserDeleteException,
)
from app.util.logging_util import log_calls

@log_calls("app.services")
class UserServiceImpl(UserService):
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def get_by_id(self, user_id: int) -> User:
        user = self.user_repository.get_by_id(user_id)
        validate_user(user, return_not_found_by_id_message(user_id))
        return user

    def get_by_email(self, email: str) -> User:
        user = self.user_repository.get_by_email(email)

        validate_user(user, return_not_found_by_email_message(email))
        return user


    def get_by_name(self, name: str) -> User:
        user = self.user_repository.get_by_name(name)
        validate_user(user, return_not_found_by_name_message(name))
        return user

    def get_all(self) -> List[User]:
        return self.user_repository.get_all()

    def save(self, user: User) -> User:
        if self.user_repository.get_by_email(user.email):
            raise DuplicateEmailException(email=user.email)
        try:
            return self.user_repository.save(user)
        except Exception as e:
            raise UserSaveException(original_exception=e)

    def update(self, user: User) -> User:
        existing_user = self.user_repository.get_by_id(user.id)
        validate_user(existing_user, return_not_found_by_id_message(user.id))

        conflict = self.user_repository.get_by_email(user.email)
        if conflict and conflict.id != user.id:
            raise DuplicateEmailException(email=user.email)

        try:
            return self.user_repository.save(user)
        except Exception as e:
            raise UserSaveException(original_exception=e)

    def delete_by_id(self, user_id: int) -> None:
        user = self.user_repository.get_by_id(user_id)
        validate_user(user, return_not_found_by_id_message(user_id))

        try:
            self.user_repository.delete_by_id(user_id)
        except Exception as e:
            raise UserDeleteException(user_id=user_id, original_exception=e)

    def exists_by_id(self, user_id: int) -> bool:
        user = self.user_repository.get_by_id(user_id)
        validate_user(user, return_not_found_by_id_message(user_id))
        return True

    def exists_by_name(self, name: str) -> bool:
        user = self.user_repository.get_by_name(name)
        validate_user(user, return_not_found_by_name_message(name))
        return True
