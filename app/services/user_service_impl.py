from typing import List, Optional
from app.models.user import User
from app.repositories.user_repository import AbstractUserRepository
from app.services.user_service import AbstractUserService
from app.error_handler.exceptions import (
    UserNotFoundException,
    DuplicateEmailException,
    UserSaveException,
    UserDeleteException,
)


class UserServiceImpl(AbstractUserService):
    def __init__(self, user_repository: AbstractUserRepository):
        self.user_repository = user_repository

    def get_by_id(self, user_id: int) -> Optional[User]:
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(user_id=user_id)
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        user = self.user_repository.get_by_email(email)
        if not user:
            raise UserNotFoundException(email=email)
        return user

    def get_by_name(self, name: str) -> Optional[User]:
        user = self.user_repository.get_by_name(name)
        if not user:
            raise UserNotFoundException(name=name)
        return user

    def get_all(self) -> List[User]:
        return self.user_repository.get_all()

    def save(self, user: User) -> User:
        existing = self.user_repository.get_by_email(user.email)
        if existing and existing.id != user.id:
            raise DuplicateEmailException(email=user.email)
        try:
            return self.user_repository.save(user)
        except Exception as e:
            raise UserSaveException(original_exception=e)

    def update(self, user: User) -> User:
        if not self.user_repository.exists_by_id(user.id):
            raise UserNotFoundException(user_id=user.id)

        existing = self.user_repository.get_by_email(user.email)
        if existing and existing.id != user.id:
            raise DuplicateEmailException(email=user.email)

        try:
            return self.user_repository.save(user)
        except Exception as e:
            raise UserSaveException(original_exception=e)

    def delete_by_id(self, user_id: int) -> None:
        if not self.user_repository.exists_by_id(user_id):
            raise UserNotFoundException(user_id=user_id)
        try:
            self.user_repository.delete_by_id(user_id)
        except Exception as e:
            raise UserDeleteException(user_id=user_id, original_exception=e)

    def exists_by_id(self, user_id: int) -> bool:
        return self.user_repository.exists_by_id(user_id)

    def exists_by_name(self, name: str) -> bool:
        return self.user_repository.exists_by_name(name)
