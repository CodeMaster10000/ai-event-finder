from abc import ABC, abstractmethod
from typing import List, Optional

from app.models.user import User


# Assuming a User model is defined elsewhere in your application
# from your_app.models import User

class UserRepository(ABC):
    """
    Abstract repository interface for managing User entities.
    """

    @abstractmethod
    def create_user(self, user: 'User') -> 'User':
        """
        Add a new user to the repository.

        :param user: The user entity to create.
        :return: The created user with any repository-assigned fields populated.
        """
        pass

    @abstractmethod
    def update_user(self, user: 'User') -> 'User':
        """
        Update an existing user in the repository.

        :param user: The user entity with updated values.
        :return: The updated user entity.
        """
        pass

    @abstractmethod
    def delete_user(self, user_id: int) -> None:
        """
        Remove a user from the repository by their unique identifier.

        :param user_id: The unique ID of the user to delete.
        """
        pass

    @abstractmethod
    def get_user(self, user_id: int) -> Optional['User']:
        """
        Retrieve a user by their unique identifier.

        :param user_id: The unique ID of the user to retrieve.
        :return: The user entity if found, otherwise None.
        """
        pass

    @abstractmethod
    def get_all_users(self) -> List['User']:
        """
        Retrieve all users from the repository.

        :return: A list of all user entities.
        """
        pass

    @abstractmethod
    def get_user_by_name(self, name: str) -> List['User']:
        """
        Find users by their name.

        :param name: The name or partial name to search for.
        :return: A list of users matching the given name.
        """
        pass
