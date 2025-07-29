import pytest
from sqlalchemy import text
from app import create_app
from app.extensions import db

@pytest.fixture
def test_app():
    app = create_app()
    with app.app_context():
        yield app  # Provides app context for the test

def test_postgres_connection_success(test_app):
    # Executes a simple SQL query to test the database connection
    result = db.session.execute(text("SELECT 1"))
    assert result.scalar() == 1
