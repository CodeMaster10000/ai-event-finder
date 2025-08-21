import secrets
from datetime import timedelta

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_migrate import upgrade as flask_migrate_upgrade
from flask_restx import Api

from app.util.model_util import warmup_local_models
from app.configuration.config import Config
from app.configuration.logging_config import configure_logging
from app.container import Container
from app.error_handler.auth_exception_handlers import register_auth_error_handlers
from app.error_handler.global_error_handler import register_error_handlers
from app.extensions import db, jwt
from app.models.user import User  # Importing all the necessary models (Users, Events, etc.)
from app.routes.app_route import app_ns
from app.routes.event_route import event_ns
from app.routes.login_route import auth_ns
from app.routes.user_route import user_ns
from app.services import user_service
from app.services import user_service_impl

from app.cli import seed_cli

migrate = Migrate()

# Function to set up REST API and Swagger API
def create_api(app: Flask):
    authorizations = {
        "BearerAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Paste your JWT token here. Format: Bearer <token>"
        }
    }

    api = Api(
        app,
        title="Event Finder API",
        version="1.0",
        description="REST API",
        doc="/swagger/",  # optional: where Swagger UI lives
        authorizations=authorizations
    )
    api.add_namespace(user_ns, path="/users")
    api.add_namespace(event_ns, path="/events")
    api.add_namespace(auth_ns, path="/auth")
    api.add_namespace(app_ns, path="/app")

# Main app factory function for Flask to create the app instance
def create_app(test_config: dict | None = None):
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["PROPAGATE_EXCEPTIONS"] = True
    CORS(app, resources={
        r"/*": {
            "origins": ["http://localhost:8080"],
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": False
        }
    })
    app.config['SECRET_KEY'] = secrets.token_hex(32)
    app.config['JWT_SECRET_KEY'] = secrets.token_urlsafe(64)
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    app.cli.add_command(seed_cli)

    if test_config and test_config.get("TESTING", True):
        app.config.update(test_config)
    else:
        with app.app_context():
            try:
                flask_migrate_upgrade()
                print("Database upgraded successfully.")
            except Exception as e:
                print(f"Error during database upgrade: {e}")

    # Dependency injection
    container = Container()
    container.init_resources()
    container.wire(modules=[
        "app.routes.user_route", "app.routes.app_route",
        "app.routes.event_route",
    ])
    app.di = container
    create_api(app)
    # Configure logging and activate error listener
    register_auth_error_handlers(app)
    configure_logging()
    register_error_handlers(app)
    warmup_local_models(container)
    @app.teardown_appcontext
    def shutdown_session(exc=None):
        # CRITICAL: returns the scoped session/connection to the pool
        db.session.remove()


    return app
