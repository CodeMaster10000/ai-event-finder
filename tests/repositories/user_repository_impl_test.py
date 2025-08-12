import pytest
from sqlalchemy.orm import scoped_session, sessionmaker

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.repositories.user_repository_impl import UserRepositoryImpl
from tests.util.util_test import test_cfg


# App fixture
@pytest.fixture
def app():
    app = create_app(test_cfg)  # test DB
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


# DB session fixture (scoped_session)
@pytest.fixture
def db_session(app):
    connection = _db.engine.connect()
    transaction = connection.begin()

    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)

    yield session  # use either session() or session directly (both work with scoped_session)

    session.remove()
    transaction.rollback()
    connection.close()


# User repository fixture
@pytest.fixture
def user_repo():
    return UserRepositoryImpl()


# ---------- Tests ----------

def test_save_user(user_repo, db_session):
    user = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    saved_user = user_repo.save(user, db_session())
    db_session.commit()

    assert saved_user.id is not None  # ID should be auto-generated
    fetched_user = user_repo.get_by_id(saved_user.id, db_session())
    assert fetched_user is not None
    assert fetched_user.name == "Alice"
    assert fetched_user.email == "alice@example.com"


def test_delete_user_by_id(user_repo, db_session):
    user = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    saved_user = user_repo.save(user, db_session())
    db_session.commit()
    assert saved_user.id is not None

    user_repo.delete_by_id(saved_user.id, db_session())
    db_session.commit()

    assert user_repo.get_by_id(saved_user.id, db_session()) is None


def test_exists_by_id(user_repo, db_session):
    user = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    saved_user = user_repo.save(user, db_session())
    db_session.commit()

    assert saved_user.id is not None
    assert user_repo.exists_by_id(saved_user.id, db_session()) is True
    assert user_repo.exists_by_id(999999, db_session()) is False


def test_get_all_users(user_repo, db_session):
    user1 = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    user2 = User(
        name="Ana",
        surname="Smith",
        email="ana@example.com",
        password="hashed-password123"
    )

    saved_user1 = user_repo.save(user1, db_session())
    saved_user2 = user_repo.save(user2, db_session())
    db_session.commit()

    fetched_users = user_repo.get_all(db_session())

    saved_ids = {saved_user1.id, saved_user2.id}
    fetched_ids = {u.id for u in fetched_users}
    assert saved_ids.issubset(fetched_ids)


def test_exists_by_name(user_repo, db_session):
    user = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    saved_user = user_repo.save(user, db_session())
    db_session.commit()

    assert saved_user.id is not None
    assert user_repo.exists_by_name(saved_user.name, db_session()) is True
    assert user_repo.exists_by_name("Nope", db_session()) is False


def test_get_by_name(user_repo, db_session):
    user = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    saved_user = user_repo.save(user, db_session())
    db_session.commit()

    assert saved_user.id is not None
    fetched_user = user_repo.get_by_name("Alice", db_session())
    assert fetched_user is not None
    assert fetched_user.id == saved_user.id


def test_get_by_email(user_repo, db_session):
    user = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    saved_user = user_repo.save(user, db_session())
    db_session.commit()

    assert saved_user.id is not None
    fetched_user = user_repo.get_by_email("alice@example.com", db_session())
    assert fetched_user is not None
    assert fetched_user.id == saved_user.id
