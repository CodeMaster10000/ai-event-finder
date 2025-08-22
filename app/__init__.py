import os
import secrets
from datetime import timedelta

from flask import Flask
from flask_migrate import Migrate
from flask_migrate import upgrade as flask_migrate_upgrade
from flask_restx import Api
from importlib import resources


from app.configuration.config import Config
from app.configuration.logging_config import configure_logging
from app.container import Container
from app.error_handler.auth_exception_handlers import register_auth_error_handlers
from app.error_handler.global_error_handler import register_error_handlers
from app.extensions import db, jwt
from app.models.user import User  # keep imports so autogenerate sees models
from app.routes.app_route import app_ns
from app.routes.event_route import event_ns
from app.routes.login_route import auth_ns
from app.routes.user_route import user_ns
from app.cli import seed_cli


PROJECT_ROOT = resources.files("app").parent
MIGRATIONS_DIR = (PROJECT_ROOT / "migrations").as_posix()

migrate = Migrate(directory=MIGRATIONS_DIR)


def create_api(app: Flask):
    api = Api(
        app,
        title="Event Finder API",
        version="1.0",
        description="REST API",
        doc="/swagger/",
        authorizations={
            "BearerAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": "Paste JWT: Bearer <token>",
            }
        },
    )
    api.add_namespace(user_ns, path="/users")
    api.add_namespace(event_ns, path="/events")
    api.add_namespace(auth_ns, path="/auth")
    api.add_namespace(app_ns, path="/app")


def create_app(test_config: dict | None = None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    app.config["PROPAGATE_EXCEPTIONS"] = True
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", secrets.token_hex(32))
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(64))
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    app.cli.add_command(seed_cli)

    # sleek auto-upgrade
    with app.app_context():
        flask_migrate_upgrade()
        env_type = "Test" if test_config and test_config.get("TESTING") else "Production"
        print(f"{env_type} database upgraded successfully.")

    container = Container()
    container.init_resources()
    container.wire(modules=[
        "app.routes.user_route",
        "app.routes.app_route",
        "app.routes.event_route",
    ])

    create_api(app)
    register_auth_error_handlers(app)
    configure_logging()
    register_error_handlers(app)

    return app