from typing import List
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService
from app.util.user_util import return_not_found_by_name_message, return_not_found_by_email_message, \
    return_not_found_by_id_message
from app.util.validation_util import validate_user
from app.util.transaction_util import transactional, retry_conflicts
from app.extensions import db
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
        user = self.user_repository.get_by_id(user_id, db.session)
        validate_user(user, return_not_found_by_id_message(user_id))
        return user

    def get_by_email(self, email: str) -> User:
        user = self.user_repository.get_by_email(email, db.session)

        validate_user(user, return_not_found_by_email_message(email))
        return user


    def get_by_name(self, name: str) -> User:
        user = self.user_repository.get_by_name(name, db.session)
        validate_user(user, return_not_found_by_name_message(name))
        return user

    def get_all(self) -> List[User]:
        return self.user_repository.get_all(db.session)

    @retry_conflicts(max_retries=3, backoff_sec=0.1)
    @transactional
    def save(self, user: User, session=None) -> User:
        if self.user_repository.get_by_email(user.email, session):
            raise DuplicateEmailException(email=user.email)
        try:
            return self.user_repository.save(user, session)
        except Exception as e:
            raise UserSaveException(original_exception=e)

    @retry_conflicts(max_retries=3, backoff_sec=0.1)
    @transactional
    def update(self, user: User, session=None) -> User:
        existing_user = self.user_repository.get_by_id(user.id, session)
        validate_user(existing_user, return_not_found_by_id_message(user.id))

        conflict = self.user_repository.get_by_email(user.email, session)
        if conflict and conflict.id != user.id:
            raise DuplicateEmailException(email=user.email)
        try:
            return self.user_repository.save(user, session)
        except Exception as e:
            raise UserSaveException(original_exception=e)

    @retry_conflicts(max_retries=3, backoff_sec=0.1)
    @transactional
    def delete_by_id(self, user_id: int, session=None) -> None:
        user = self.user_repository.get_by_id(user_id, session)
        validate_user(user, return_not_found_by_id_message(user_id))

        try:
            self.user_repository.delete_by_id(user_id, session)
        except Exception as e:
            raise UserDeleteException(user_id=user_id, original_exception=e)

    def exists_by_id(self, user_id: int) -> bool:
        user = self.user_repository.get_by_id(user_id, db.session)
        validate_user(user, return_not_found_by_id_message(user_id))
        return True

    def exists_by_name(self, name: str) -> bool:
        user = self.user_repository.get_by_name(name, db.session)
        validate_user(user, return_not_found_by_name_message(name))
        return True
