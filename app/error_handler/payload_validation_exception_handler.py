from werkzeug.exceptions import HTTPException


class InvalidUserData(HTTPException):
    code = 400
    description = "Invalid user data"

    def __init__(self, errors):
        """
        :param errors: a dict or string describing what went wrong
        """
        # Pass your errors into the .description so that Flask’s error handler
        # will include them in the response.
        super().__init__(description=errors)
