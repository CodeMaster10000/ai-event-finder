from abc import ABC, abstractmethod
from typing import Optional, List

from app.models.user import User


class AbstractUserRepository(ABC):
    """
    Interface for User repository operations.
    """

    def __init__(self, session):
        """
        Initialize the repository with a database session.

        :param session: The database session or connection.
        """
        self.session = session

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Retrieve a user by its unique identifier.

        :param user_id: The primary key of the user.
        :return: The User instance if found, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by their email address.

        :param email: The user's email.
        :return: The User instance if found, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[User]:
        """
        Retrieve a user by their name.

        :param name: The user's name.
        :return: The User instance if found, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> List[User]:
        """
        Retrieve all users in the system.

        :return: A list of all User instances.
        """
        raise NotImplementedError

    @abstractmethod
    def save(self, user: User) -> User:
        """
        Persist a new user or update an existing one.

        :param user: The User instance to save.
        :return: The saved User instance (with any DB-generated fields populated).
        """
        raise NotImplementedError

    @abstractmethod
    def delete_by_id(self, user_id: int) -> None:
        """
        Delete a user given their unique identifier.

        :param user_id: The primary key of the user to delete.
        :raises UserNotFound: If no user exists with the given ID.
        :raises AppException: If the deletion fails at the database level.
        """
        raise NotImplementedError

    @abstractmethod
    def exists_by_id(self, user_id: int) -> bool:
        """
        Check whether a user exists by their ID.

        :param user_id: The primary key to check.
        :return: True if a user with that ID exists, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def exists_by_name(self, name: str) -> bool:
        """
        Check whether a user exists by their name.

        :param name: The user's name to check.
        :return: True if a user with that name exists, False otherwise.
        """
        raise NotImplementedError
