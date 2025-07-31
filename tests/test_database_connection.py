import pytest
from sqlalchemy import text
from app import create_app
from app.extensions import db
from tests.util.test_util import test_cfg

@pytest.fixture
def app():

    app = create_app(test_cfg)
    with app.app_context():
        yield app

def test_postgres_connection_success(app):
    result = db.session.execute(text("SELECT 1"))
    assert result.scalar() == 1
