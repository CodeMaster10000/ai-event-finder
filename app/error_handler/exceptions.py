class UserNotFoundException(Exception):
    """
    This exception will be raised when no user exists for the given identifier.
    You must pass exactly one of the following: user_id, name, email!
    """

    def __init__(self, *,
        user_id : int | None = None,
        name: str | None = None,
        email: str | None = None,
                 ):
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
        identifiers ={
            "id":user_id,
            "name":name,
            "email":email
        }
        provided = [(k,v) for k,v in identifiers.items() if v is not None]
        if len(provided) != 1:
            raise ValueError(
                "UserNotFoundException requires exactly one of "
                "user_id, name, or email"
            )

        field, value = provided[0]
        message = f"User with {field}={value} not found."
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
