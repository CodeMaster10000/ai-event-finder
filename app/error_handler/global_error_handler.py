"""
Global error handler registrations for the Flask application.
Each handler catches a specific exception type, logs if necessary,
and returns a JSON error response with an appropriate HTTP status.
"""

from flask import jsonify
from app.error_handler.exceptions import (
    UserNotFoundException,
    DuplicateEmailException,
    UserSaveException,
    UserDeleteException,
)


def register_error_handlers(app):
    """
    Attach custom exception handlers to the given Flask app.

    Args:
        app (Flask): The Flask application instance.
    """

    @app.errorhandler(UserNotFoundException)
    def handle_user_not_found(exception):
        """
        404: User lookup by ID, name, or email failed.
        """
        # error logging centralized in logging_config instead

        response = {
            "error": {
                "code": "USER_NOT_FOUND",
                "message": str(exception),
            }
        }
        return jsonify(response), 404

    @app.errorhandler(DuplicateEmailException)
    def handle_duplicate_email(exception):
        """
        409: Attempt to create or update a user with an existing email.
        """
        # error logging centralized in logging_config instead

        response = {
            "error": {
                "code": "DUPLICATE_EMAIL",
                "message": str(exception),
            }
        }
        return jsonify(response), 409

    @app.errorhandler(UserSaveException)
    def handle_user_save(exception):
        """
        500: Saving (creating/updating) a user failed due to an internal error.
        Logs the original exception if available.
        """
        # error logging centralized in logging_config instead

        response = {
            "error": {
                "code": "USER_SAVE_ERROR",
                "message": str(exception),
            }
        }
        return jsonify(response), 500

    @app.errorhandler(UserDeleteException)
    def handle_user_delete(exception):
        """
        500: Deleting a user failed due to an internal error.
        Logs the original exception if available.
        """
        # error logging centralized in logging_config instead

        response = {
            "error": {
                "code": "USER_DELETE_ERROR",
                "message": str(exception),
            }
        }
        return jsonify(response), 500
