class UserNotFoundException(Exception):
    """
    This exception will be raised when no user exists for the given identifier.
    You must pass exactly one of the following: user_id, name, email!
    """

    def __init__(self, message:str ):
        """
        One of the following: user_id, name, email must be explicitly passed
        when raising the exception.
        Example:
            raise UserNotFoundException(user_id=5)
            raise UserNotFoundException(name="John")
            raise UserNotFoundException(email="john@doe.com")
        """

        """
            We use the identifiers dictionary and provided list to make sure that 
            only one identifier was passed when raising the exception.
        """

        super().__init__(message)

class DuplicateEmailException(Exception):
    """
    This exception will be raised when attempting to
    create or update a user with an email that's already taken.
    """
    def __init__(self, email:str):
        self.email = email
        message = f"User with email {email} already exists."
        super().__init__(message)

class UserSaveException(Exception):
    """
    Raised when persisting a user to the database fails.
    Attributes:
        original_exception (Exception|None): The underlying exception.
    """
    def __init__(self, original_exception: Exception = None):
        self.original_exception = original_exception
        # generic message only
        message = "Unable to save user due to an internal error."
        super().__init__(message)


class UserDeleteException(Exception):
    """
    Raised when deleting a user from the database fails (aside from not found).
    Attributes:
        user_id (int|None): ID of the user we tried to delete.
        original_exception (Exception|None): The underlying exception.
    """
    def __init__(self, user_id: int = None, original_exception: Exception = None):
        self.user_id = user_id
        self.original_exception = original_exception
        # generic message only
        message = f"Unable to delete user{f' with id={user_id}' if user_id is not None else ''}."
        super().__init__(message)

class EventNotFoundException(Exception):
    def __init__(self, message):
        super().__init__(message)

class EventSaveException(Exception):
    def __init__(self, original_exception: Exception = None):
        self.original_exception = original_exception

        message = "Unable to save event due to an internal error."
        super().__init__(message)

class EventDeleteException(Exception):
    """
    Raised when deleting an event from the database fails (aside from not found).
    Attributes:
        event_id (int|None): ID of the event we tried to delete.
        original_exception (Exception|None): The underlying exception.
    """
    def __init__(self, event_id: int = None, original_exception: Exception = None):
        self.event_id = event_id
        self.original_exception = original_exception

        message = f"Unable to delete event{f' with id={event_id}' if event_id is not None else ''}."
        super().__init__(message)

class EventAlreadyExistsException(Exception):
    def __init__(self, event_name: str, original_exception: Exception = None):
        self.original_exception = original_exception

        message = f"Event with name {event_name} already exists."
        super().__init__(message)

class UserAlreadyInEventException(Exception):
    def __init__(self, event_title: str, user_email:str):
        self.event_title = event_title
        self.user_email = user_email
        message = f"User with email {user_email} already exists in event with title {event_title}."
        super().__init__(message)


class UserNotInEventException(Exception):
    def __init__(self, event_title: str, user_email:str):
        self.event_title = event_title
        self.user_email = user_email
        message = f"User with email {user_email} doesn't exist in event with title {event_title}."
        super().__init__(message)

class EventSaveException(Exception):
    """
    Raised when persisting an event fails due to an internal error.
    """

    def __init__(self, original_exception: Exception):
        super().__init__("Unable to save event due to an internal error.")
        self.original_exception = original_exception


class EmbeddingVectorException(Exception):
    """
    Raised when encountering embedding vector fails (like wrong vector_dim)
    """
    def __init__(self, message: str):
        super().__init__(message)





