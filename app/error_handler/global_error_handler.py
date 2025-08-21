import logging
import traceback

from flask import jsonify, request
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException, UnsupportedMediaType, BadRequest, RequestEntityTooLarge


def register_error_handlers(app):
    """
    Error handlers compatible with Flask-RESTX
    """
    
    logger = logging.getLogger(__name__)

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
        UserAlreadyInEventException,
        ConcurrencyException,
        EmbeddingServiceException
    )

    @app.errorhandler(ValidationError)
    def handle_marshmallow_validation(err: ValidationError):
        # err.messages is a dict of field -> list[str]
        return jsonify({"error": {"code": "VALIDATION_ERROR","message": "Invalid request payload.","fields": err.messages,}}), 422

    # --- NEW: JSON/body issues ---
    @app.errorhandler(BadRequest)
    def handle_bad_request(err: BadRequest):
        # e.g. malformed JSON -> “Failed to decode JSON object …”
        return jsonify({"error": {"code": "BAD_REQUEST", "message": err.description or "Bad request."}}), 400

    @app.errorhandler(UnsupportedMediaType)
    def handle_unsupported_media(err: UnsupportedMediaType):
        return jsonify({"error": { "code": "UNSUPPORTED_MEDIA_TYPE","message": err.description or "Unsupported media type."}}), 415

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(err: RequestEntityTooLarge):
        return jsonify({ "error": { "code": "REQUEST_ENTITY_TOO_LARGE","message": "Payload too large."}}), 413

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

    @app.errorhandler(ConcurrencyException)
    def handle_concurrency_exception(exception):
        return jsonify({"error": {"code": "CONCURRENT_UPDATE", "message": str(exception)}}), 409

    @app.errorhandler(EmbeddingServiceException)
    def handle_embedding_service_error(exception: EmbeddingServiceException):
        # log provider/root cause if present (shows full stack in server logs)
        if getattr(exception, "original_exception", None):
            logger.exception("Embedding service error", exc_info=exception.original_exception)

        return jsonify({"error": {"code": "EMBEDDING_SERVICE_ERROR","message": str(exception),}}), getattr(exception, "status_code", 500)


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

