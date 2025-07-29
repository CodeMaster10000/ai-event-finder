from flask import Flask
from flask_restx import Api

from app.configuration.config import Config
from app.container import Container
# from app.routes.user_route import user_ns
from app.extensions import db
from app.services import user_service

# Function to set up REST API and Swagger API
def create_api(app: Flask):
    api = Api(
        app,
        title="Event Finder API",
        version="1.0",
        description="REST API",
        doc="/swagger/"  # optional: where Swagger UI lives
    )
    #api.add_namespace(user_ns, path="/users")


# Main app factory function for Flask to create the app instance
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)

    # Dependency injection
    container = Container()
    container.init_resources()
    container.wire(modules=[
        "app.routes.user_route"
    ])

    create_api(app)

    return app
