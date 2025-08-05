import pytest
from datetime import datetime
from flask import Flask

from app.extensions import db
from app.models.event import Event, guest_list
from app.models.user import User
from app.util.event_util import (
    TITLE_MAX_LENGTH,
    DESCRIPTION_MAX_LENGTH,
    LOCATION_MAX_LENGTH,
    CATEGORY_MAX_LENGTH,
)


def setup_module(module):
    """
    Ensure models are imported so SQLAlchemy tables are registered.
    """
    # No-op: imports above suffice
    pass

@pytest.fixture(scope="module")
def app():
    """
    Create a Flask application configured for an in-memory SQLite DB.
    """
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture(scope="module")
def session(app):
    """
    Provide a SQLAlchemy session for tests.
    """
    return db.session


def test_guest_list_table_definition():
    """
    The guest_list association table should have correct name and columns.
    """
    assert guest_list.name == "guest_list"
    cols = {col.name for col in guest_list.columns}
    assert cols == {"event_id", "user_id"}
    # Each column should have a foreign key to the correct table
    fk_tables = {fk.column.table.name for col in guest_list.columns for fk in col.foreign_keys}
    assert fk_tables == {"events", "user"}


def test_tablename_and_columns():
    """
    Event.__tablename__ and its columns should match the model.
    """
    assert Event.__tablename__ == "events"
    column_names = {c.name for c in Event.__table__.columns}
    expected = {"id", "title", "datetime", "description", "organizer_id", "location", "category"}
    assert expected.issubset(column_names)


def test_column_length_constraints():
    """
    String column lengths should match constants in event_util.
    """
    cols = Event.__table__.columns
    assert cols["title"].type.length == TITLE_MAX_LENGTH
    assert cols["description"].type.length == DESCRIPTION_MAX_LENGTH
    assert cols["location"].type.length == LOCATION_MAX_LENGTH
    assert cols["category"].type.length == CATEGORY_MAX_LENGTH


def test_repr_without_db():
    """
    __repr__ on an unsaved Event should include id, title, and datetime.
    """
    dt = datetime(2025, 8, 1, 12, 0)
    e = Event(id=123, title="Sample", datetime=dt, description=None, organizer_id=1, location="X", category="Y")
    assert repr(e) == f"<Event 123 – Sample @ {dt}>"


def test_persistence_and_relationships(session):
    """
    Persist Event and User, check __repr__, and test guests relationship.
    """
    # Create organizer
    org = User(name="Org", surname="One", email="org@example.com", password="pw")
    session.add(org)
    session.commit()

    # Create event
    dt = datetime(2025, 8, 2, 18, 30)
    ev = Event(title="Party", datetime=dt, description="Fun", organizer=org, location="Club", category="Social")
    session.add(ev)
    session.commit()

    # __repr__ with real id
    assert repr(ev) == f"<Event {ev.id} – Party @ {dt}>"

    # Add guest
    guest = User(name="Guest", surname="User", email="guest@example.com", password="pw")
    session.add(guest)
    session.commit()

    ev.guests.append(guest)
    session.commit()

    # dynamic relationship returns list
    guests = ev.guests.all()
    assert guest in guests
    # filtered query
    assert ev.guests.filter_by(email="guest@example.com").first() == guest
