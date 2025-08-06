from flask_jwt_extended import create_access_token

def generate_test_token(app, user_id: int) -> str:
    """
    Generates a JWT token for testing purposes using the provided app context.
    """
    with app.app_context():
        return create_access_token(identity=str(user_id))