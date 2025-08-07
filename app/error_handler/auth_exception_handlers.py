from flask import jsonify
from app.extensions import jwt

def register_auth_error_handlers(app):
    """
    Initialize JWTManager and register JWT-specific error handlers.
    Call this early in your app factory, before any catch-all handlers.
    """
    # Make sure the JWTManager is bound to this app
    jwt.init_app(app)

    @jwt.unauthorized_loader
    def missing_token_callback(reason):
        # No / Authorization header, or wrong header name
        return jsonify({
            "error": {
                "code": "JWT_MISSING",
                "message": reason
            }
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        # Malformed token, bad signature, etc.
        return jsonify({
            "error": {
                "code": "JWT_INVALID",
                "message": reason
            }
        }), 422

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        # Token was valid but expired
        return jsonify({
            "error": {
                "code": "JWT_EXPIRED",
                "message": "Token has expired"
            }
        }), 401
