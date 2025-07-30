from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.user import User


class AbstractUserService(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[User]:
        pass

    @abstractmethod
    def get_all(self) -> List[User]:
        pass

    @abstractmethod
    def save(self, user: User) -> User:
        pass

    @abstractmethod
    def delete_by_id(self, user_id: int) -> None:
        pass

    @abstractmethod
    def exists_by_id(self, user_id: int) -> bool:
        pass

    @abstractmethod
    def exists_by_name(self, name: str) -> bool:
        pass