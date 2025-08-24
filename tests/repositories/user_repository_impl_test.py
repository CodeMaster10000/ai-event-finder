# tests/repositories/user_repository_impl_test.py
import pytest
from sqlalchemy.orm import scoped_session, sessionmaker

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.repositories.user_repository_impl import UserRepositoryImpl
from tests.util.util_test import test_cfg


@pytest.fixture(scope="session")
def app():
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


@pytest.fixture
def user_repo():
    return UserRepositoryImpl()


def test_get_all_users(user_repo, db_session):
    u1 = User(name="Alice", surname="Smith", email="alice@example.com", password="hashed-password")
    u2 = User(name="Ana",   surname="Smith", email="ana@example.com",   password="hashed-password123")

    s1 = user_repo.save(u1, db_session())
    s2 = user_repo.save(u2, db_session())
    db_session.commit()

    fetched = user_repo.get_all(db_session())
    saved_ids = {s1.id, s2.id}
    fetched_ids = {u.id for u in fetched}
    assert saved_ids.issubset(fetched_ids)


def test_get_by_id(user_repo, db_session):
    u = User(name="Alice", surname="Smith", email="alice@example.com", password="hashed-password")
    s = user_repo.save(u, db_session())
    db_session.commit()

    fetched = user_repo.get_by_id(s.id, db_session)
    assert fetched is not None
    assert fetched.id == s.id


def test_get_by_name(user_repo, db_session):
    u = User(name="Alice", surname="Smith", email="alice@example.com", password="hashed-password")
    s = user_repo.save(u, db_session())
    db_session.commit()

    fetched = user_repo.get_by_name("Alice", db_session)
    assert fetched is not None
    assert fetched.id == s.id


def test_get_by_email(user_repo, db_session):
    u = User(name="Alice", surname="Smith", email="alice@example.com", password="hashed-password")
    s = user_repo.save(u, db_session())
    db_session.commit()

    fetched = user_repo.get_by_email("alice@example.com", db_session)
    assert fetched is not None
    assert fetched.id == s.id


def test_exists_by_id(user_repo, db_session):
    u = User(name="Alice", surname="Smith", email="alice@example.com", password="hashed-password")
    s = user_repo.save(u, db_session())
    db_session.commit()

    assert user_repo.exists_by_id(s.id, db_session) is True
    assert user_repo.exists_by_id(999999, db_session) is False


def test_exists_by_name(user_repo, db_session):
    u = User(name="Alice", surname="Smith", email="alice@example.com", password="hashed-password")
    s = user_repo.save(u, db_session())
    db_session.commit()

    assert user_repo.exists_by_name(s.name, db_session) is True
    assert user_repo.exists_by_name("Nope", db_session) is False


def test_delete_user_by_id(user_repo, db_session):
    u = User(name="Alice", surname="Smith", email="alice@example.com", password="hashed-password")
    s = user_repo.save(u, db_session())
    db_session.commit()

    user_repo.delete_by_id(s.id, db_session)
    db_session.commit()

    assert user_repo.get_by_id(s.id, db_session) is None
