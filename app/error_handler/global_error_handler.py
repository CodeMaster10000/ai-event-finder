from flask import jsonify
from app.error_handler.exceptions import UserNotFoundException

def register_error_handlers(app):
    @app.errorhandler(UserNotFoundException)
    def handle_user_not_found(exception):
        response = {
            "error": {
                "code": "USER_NOT_FOUND",
                "message":str(exception),
            }
        }
        return jsonify(response), 404

