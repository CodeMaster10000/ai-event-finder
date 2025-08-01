from app.configuration.logging_config import configure_logging
import logging
from flask import Flask
from flask_migrate import Migrate
from flask_restx import Api
from app.configuration.config import Config
from app.container import Container
from app.error_handler.global_error_handler import register_error_handlers
from app.extensions import db
from app.models.user import User  # Importing all the necessary models (Users, Events, etc.)
from flask_migrate import upgrade as flask_migrate_upgrade



from app.routes.user_route import user_ns
from app.services import user_service
from app.services import user_service_impl


migrate = Migrate()

# Function to set up REST API and Swagger API
def create_api(app: Flask):
    api = Api(
        app,
        title="Event Finder API",
        version="1.0",
        description="REST API",
        doc="/swagger/"  # optional: where Swagger UI lives
    )
    api.add_namespace(user_ns, path="/users")

# Main app factory function for Flask to create the app instance
def create_app(test_config: dict | None = None):
    configure_logging()
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
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
        "app.routes.user_route"
    ])

    create_api(app)
    # Configure logging and activate error listener
    configure_logging()
    register_error_handlers(app)


    return app
