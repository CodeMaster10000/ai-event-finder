from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.user import User


class AbstractUserService(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Retrieve a user by their unique ID."""
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve a user by their email address."""
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[User]:
        """Retrieve a user by their name."""
        pass

    @abstractmethod
    def get_all(self) -> List[User]:
        """Retrieve a list of all users."""
        pass

    @abstractmethod
    def save(self, user: User) -> User:
        """Create a new user or update an existing user."""
        pass

    @abstractmethod
    def update(self, user: User) -> User:
        """Update an existing user's data."""
        pass

    @abstractmethod
    def delete_by_id(self, user_id: int) -> None:
        """Delete a user by their ID. Raise an error if not found."""
        pass

    @abstractmethod
    def exists_by_id(self, user_id: int) -> bool:
        """Check whether a user exists by their ID."""
        pass

    @abstractmethod
    def exists_by_name(self, name: str) -> bool:
        """Check whether a user exists by their name."""
        pass

    @abstractmethod
    def exists_by_id(self, user_id: int) -> bool:
        pass

    @abstractmethod
    def exists_by_name(self, name: str) -> bool:
        pass