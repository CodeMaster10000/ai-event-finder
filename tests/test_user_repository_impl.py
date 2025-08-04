import pytest
from sqlalchemy.orm import scoped_session, sessionmaker

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.repositories.user_repository_impl import UserRepositoryImpl
from tests.util.test_util import test_cfg


# App fixture
@pytest.fixture
def app():
    app = create_app(test_cfg)  # make sure "testing" uses a test DB
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()

# DB session fixture
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

# User repository fixture
@pytest.fixture
def user_repo(db_session):
    return UserRepositoryImpl(db_session())

# Testing the save method
def test_save_user(user_repo):
    user = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    saved_user = user_repo.save(user)
    user_repo.session.commit()

    assert saved_user.id is not None  # ID should be auto-generated
    fetched_user = user_repo.get_by_id(saved_user.id)
    assert fetched_user is not None
    assert fetched_user.name == "Alice"
    assert fetched_user.email == "alice@example.com"

def test_delete_user_by_id(user_repo):
    user = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    saved_user = user_repo.save(user)
    user_repo.session.commit()

    assert saved_user.id is not None

    user_repo.delete_by_id(saved_user.id)
    user_repo.session.commit()

    assert user_repo.get_by_id(saved_user.id) is None

def test_exists_by_id(user_repo):
    user = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    saved_user = user_repo.save(user)
    user_repo.session.commit()

    assert saved_user.id is not None  # ID should be auto-generated
    fetched_user = user_repo.exists_by_id(saved_user.id)
    assert fetched_user is True

def test_get_all_users(user_repo):
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

    saved_user1 = user_repo.save(user1)
    saved_user2 = user_repo.save(user2)
    user_repo.session.commit()

    fetched_users = user_repo.get_all()

    saved_ids = {saved_user1.id, saved_user2.id}
    fetched_ids = {user.id for user in fetched_users}

    assert saved_ids.issubset(fetched_ids)

def test_exists_by_name(user_repo):
    user = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    saved_user = user_repo.save(user)
    user_repo.session.commit()

    assert saved_user.id is not None  # ID should be auto-generated
    fetched_user = user_repo.exists_by_name(saved_user.name)
    assert fetched_user is True

def test_get_by_name(user_repo):
    user = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    saved_user = user_repo.save(user)
    user_repo.session.commit()

    assert saved_user.id is not None
    fetched_user = user_repo.get_by_name("Alice")
    assert fetched_user is not None

def test_get_by_email(user_repo):
    user = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    saved_user = user_repo.save(user)
    user_repo.session.commit()

    assert saved_user.id is not None
    fetched_user = user_repo.get_by_email("alice@example.com")
    assert fetched_user is not None


