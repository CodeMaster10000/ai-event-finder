import logging
import traceback

from flask import jsonify, request
from werkzeug.exceptions import HTTPException

from app.error_handler.exceptions import EmbeddingServiceException

from app.error_handler.exceptions import InvalidUserData


def register_error_handlers(app):
    """
    Error handlers compatible with Flask-RESTX
    """
    
    logger = logging.getLogger(__name__)
    
    # -------------------------
    # JWT ERROR HANDLERS (these work with Flask-JWT-Extended)
    # -------------------------

    # -------------------------
    # FLASK APP ERROR HANDLERS
    # -------------------------

    # Custom exception handlers (your existing ones)
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

    @app.errorhandler(UserNotFoundException)
    def handle_user_not_found(exception):
        return jsonify({"error": {"code": "USER_NOT_FOUND", "message": str(exception)}}), 404

    @app.errorhandler(DuplicateEmailException)
    def handle_duplicate_email(exception):
        return jsonify({"error": {"code": "DUPLICATE_EMAIL", "message": str(exception)}}), 409

    @app.errorhandler(UserSaveException)
    def handle_user_save(exception):
        return jsonify({"error": {"code": "USER_SAVE_ERROR", "message": str(exception)}}), 500

    @app.errorhandler(UserDeleteException)
    def handle_user_delete(exception):
        return jsonify({"error": {"code": "USER_DELETE_ERROR", "message": str(exception)}}), 500

    @app.errorhandler(EventNotFoundException)
    def handle_event_not_found(exception):
        return jsonify({"error": {"code": "EVENT_NOT_FOUND", "message": str(exception)}}), 404

    @app.errorhandler(EventAlreadyExistsException)
    def handle_event_already_exists(exception):
        return jsonify({"error": {"code": "EVENT_ALREADY_EXISTS", "message": str(exception)}}), 409

    @app.errorhandler(EventSaveException)
    def handle_event_save(exception):
        return jsonify({"error": {"code": "EVENT_SAVE_ERROR", "message": str(exception)}}), 500

    @app.errorhandler(EventDeleteException)
    def handle_event_delete(exception):
        return jsonify({"error": {"code": "EVENT_DELETE_ERROR", "message": str(exception)}}), 500

    @app.errorhandler(UserNotInEventException)
    def handle_user_not_in_event(exception):
        return jsonify({"error": {"code": "USER_NOT_IN_EVENT", "message": str(exception)}}), 404

    @app.errorhandler(UserAlreadyInEventException)
    def handle_user_already_in_event(exception):
        return jsonify({"error": {"code": "USER_ALREADY_IN_EVENT", "message": str(exception)}}), 409

    @app.error_handler(InvalidUserData)
    def handle_invalid_user_data(exception):
        return jsonify({"error": {"code": "INVALID_USER_DATA", "message": str(exception)}}), 400



    @app.errorhandler(EmbeddingServiceException)
    def handle_embedding_error(exception):
        return jsonify({"error": {"code": "EMBEDDING_SERVICE_ERROR", "message": str(exception)}}), 500

    # -------------------------
    # GLOBAL FALLBACK - DETAILED DEBUGGING
    # -------------------------

    @app.errorhandler(Exception)
    def handle_all_exceptions(e):
        logger.error("="*60)
        logger.error(f"UNHANDLED EXCEPTION: {type(e).__name__}")
        logger.error(f"Message: {str(e)}")
        logger.error(f"Module: {type(e).__module__}")
        logger.error(f"Request: {request.method} {request.url}")
        logger.error(f"Headers: {dict(request.headers)}")
        
        # Print the full traceback
        logger.error("Full traceback:")
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                logger.error(line)
        logger.error("="*60)
        
        # Handle HTTPExceptions
        if isinstance(e, HTTPException):
            return jsonify({
                "error": {
                    "code": e.name.upper().replace(" ", "_"),
                    "message": e.description,
                }
            }), e.code

        # Generic 500 error
        return jsonify({
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": f"Unexpected error: {type(e).__name__}"
            }
        }), 500