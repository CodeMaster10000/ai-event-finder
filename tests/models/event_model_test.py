# tests/models/event_model_test.py

import pytest
from datetime import datetime

from app import create_app
from app.configuration.config import Config
from app.extensions import db as _db
from app.models.event import Event, guest_list
from app.models.user import User
from app.constants import (
    TITLE_MAX_LENGTH,
    DESCRIPTION_MAX_LENGTH,
    LOCATION_MAX_LENGTH,
    CATEGORY_MAX_LENGTH,
)
from sqlalchemy.orm import scoped_session, sessionmaker


# ---------- App / DB setup ----------

@pytest.fixture(scope="session")
def app():
    from tests.util.util_test import test_cfg
    app = create_app(test_cfg)
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield app
        _db.session.remove()


@pytest.fixture(autouse=True)
def clean_db(app):
    with app.app_context():
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture
def db_session(app):
    connection = _db.engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)

    yield session

    session.remove()
    transaction.rollback()
    connection.close()


# ---------- Tests ----------

def test_guest_list_table_definition():
    assert guest_list.name == "guest_list"
    col_names = {c.name for c in guest_list.columns}
    assert col_names == {"event_id", "user_id"}
    fk_tables = {fk.column.table.name for col in guest_list.columns for fk in col.foreign_keys}
    assert fk_tables == {"events", "user"}


def test_tablename_and_columns():
    assert Event.__tablename__ == "events"
    cols = {c.name for c in Event.__table__.columns}
    expect = {"id", "title", "datetime", "description", "organizer_id", "location", "category", "embedding", "version"}
    assert expect.issubset(cols)


def test_column_length_constraints():
    cols = Event.__table__.columns
    assert cols["title"].type.length == TITLE_MAX_LENGTH
    assert cols["description"].type.length == DESCRIPTION_MAX_LENGTH
    assert cols["location"].type.length == LOCATION_MAX_LENGTH
    assert cols["category"].type.length == CATEGORY_MAX_LENGTH


def test_repr_without_db():
    dt = datetime(2025, 8, 1, 12, 0)
    e = Event(id=123, title="Sample", datetime=dt, description=None, organizer_id=1, location="X", category="Y")
    assert repr(e) == f"<Event 123 – Sample @ {dt.isoformat()}>"


def test_persistence_and_relationships(db_session):
    sess = db_session()

    org = User(name="Org", surname="One", email="org@example.com", password="pw")
    sess.add(org)
    sess.commit()

    dt = datetime(2025, 8, 2, 18, 30)
    ev = Event(
        title="Party",
        datetime=dt,
        description="Fun",
        organizer=org,
        location="Club",
        category="Social",
        embedding=[0.0] * Config.UNIFIED_VECTOR_DIM,
    )
    sess.add(ev)
    sess.commit()

    assert repr(ev) == f"<Event {ev.id} – Party @ {dt.isoformat()}>"

    guest = User(name="Guest", surname="User", email="guest@example.com", password="pw")
    sess.add(guest)
    sess.commit()

    ev.guests.append(guest)
    sess.commit()

    guests_list = ev.guests.all()
    assert guest in guests_list
    assert ev.guests.filter_by(email="guest@example.com").first() == guest