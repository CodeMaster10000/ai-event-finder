from typing import List, Optional
from app.models.user import User
from app.repositories.user_repository import AbstractUserRepository
from app.services.user_service import AbstractUserService


class UserServiceImpl(AbstractUserService):
    def __init__(self, user_repository: AbstractUserRepository):
        self.user_repository = user_repository

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.user_repository.get_by_id(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        return self.user_repository.get_by_email(email)

    def get_by_name(self, name: str) -> Optional[User]:
        return self.user_repository.get_by_name(name)

    def get_all(self) -> List[User]:
        return self.user_repository.get_all()

    def save(self, user: User) -> User:
        existing = self.user_repository.get_by_email(user.email)
        if existing and existing.id != user.id:
            raise ValueError(f"User with email {user.email} already exists.")
        return self.user_repository.save(user)

    def delete_by_id(self, user_id: int) -> None:
        if not self.user_repository.exists_by_id(user_id):
            raise ValueError(f"User with ID {user_id} not found.")
        self.user_repository.delete_by_id(user_id)

    def exists_by_id(self, user_id: int) -> bool:
        return self.user_repository.exists_by_id(user_id)

    def exists_by_name(self, name: str) -> bool:
        return self.user_repository.exists_by_name(name)
