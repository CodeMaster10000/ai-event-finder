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
    EventNotFoundException,
    EventAlreadyExistsException,
    EventSaveException,
    EventDeleteException,
    UserNotInEventException,
    UserAlreadyInEventException
)


def register_error_handlers(app):
    """
    Attach custom exception handlers to the given Flask app.

    Args:
        app (Flask): The Flask application instance.
    """

    # -------------------------
    # USER EXCEPTION HANDLERS
    # -------------------------

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

        # -------------------------
        # EVENT EXCEPTION HANDLERS
        # -------------------------

    @app.errorhandler(EventNotFoundException)
    def handle_event_not_found(exception):
        """
        404: Requested event could not be found by title or ID.
        """
        response = {
            "error": {
                "code": "EVENT_NOT_FOUND",
                "message": str(exception),
            }
        }
        return jsonify(response), 404

    @app.errorhandler(EventAlreadyExistsException)
    def handle_event_already_exists(exception):
        """
        409: Attempt to create an event with a title that already exists.
        """
        response = {
            "error": {
                "code": "EVENT_ALREADY_EXISTS",
                "message": str(exception),
            }
        }
        return jsonify(response), 409

    @app.errorhandler(EventSaveException)
    def handle_event_save(exception):
        """
        500: Saving (creating/updating) an event failed due to an internal error.
        """
        response = {
            "error": {
                "code": "EVENT_SAVE_ERROR",
                "message": str(exception),
            }
        }
        return jsonify(response), 500

    @app.errorhandler(EventDeleteException)
    def handle_event_delete(exception):
        """
        500: Deleting an event failed due to an internal error.
        """
        response = {
            "error": {
                "code": "EVENT_DELETE_ERROR",
                "message": str(exception),
            }
        }
        return jsonify(response), 500

    # -------------------------------
    # PARTICIPANT EXCEPTION HANDLERS
    # -------------------------------

    @app.errorhandler(UserNotInEventException)
    def handle_user_not_in_event(exception):
        """
        404: Attempted to remove or list a user who is not a participant in the event.
        """
        response = {
            "error": {
                "code": "USER_NOT_IN_EVENT",
                "message": str(exception),
            }
        }
        return jsonify(response), 404

    @app.errorhandler(UserAlreadyInEventException)
    def handle_user_already_in_event(exception):
        """
        409: Attempted to add a user to an event they're already participating in.
        """
        response = {
            "error": {
                "code": "USER_ALREADY_IN_EVENT",
                "message": str(exception),
            }
        }
        return jsonify(response), 409
