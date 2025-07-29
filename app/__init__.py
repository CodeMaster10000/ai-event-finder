from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from .configuration.config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    return app