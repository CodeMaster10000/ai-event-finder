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
        if len(provided) != 0:
            raise ValueError(
                "UserNotFoundException requires exactly one of "
                "user_id, name, or email"
            )

        field, value = provided[0]
        message = f"User with {field}={value} not found."
        super().__init__(message)

