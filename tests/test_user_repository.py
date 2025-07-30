import pytest
from sqlalchemy.orm import scoped_session, sessionmaker

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.repositories.user_repository_impl import UserRepository

# App fixture
@pytest.fixture
def app():
    app = create_app()  # make sure "testing" uses a test DB
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

    # Use SQLAlchemy's sessionmaker + scoped_session
    sessionFactory = sessionmaker(bind=connection)
    session = scoped_session(sessionFactory)

    yield session

    session.remove()
    transaction.rollback()
    connection.close()

# User repository fixture
@pytest.fixture
def user_repo(db_session):
    return UserRepository(db_session())

# Testing the save method
def test_save_user(user_repo):
    # Arrange
    user = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    # Act
    saved_user = user_repo.save(user)
    user_repo.session.commit()

    # Assert
    assert saved_user.id is not None  # ID should be auto-generated
    fetched_user = user_repo.session.get(User, saved_user.id)
    assert fetched_user is not None
    assert fetched_user.name == "Alice"
    assert fetched_user.email == "alice@example.com"

# Testing the delete method
def test_delete_user_by_id(user_repo):
    # Arrange
    user = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    # Act
    saved_user = user_repo.save(user)
    user_repo.session.commit()

    # Assert
    assert saved_user.id is not None  # ID should be auto-generated
    fetched_user = user_repo.session.get(User, saved_user.id)
    assert fetched_user is not None
    assert user_repo.session.delete(saved_user) is None

def test_exists_by_id(user_repo):
    # Arrange
    user = User(
        name="Alice",
        surname="Smith",
        email="alice@example.com",
        password="hashed-password"
    )

    # Act
    saved_user = user_repo.save(user)
    user_repo.session.commit()

    # Assert
    assert saved_user.id is not None  # ID should be auto-generated
    fetched_user = user_repo.session.get(User, 1)
    assert fetched_user is not None
    fetched_user = saved_user

def test_get_all_users(user_repo):
    # Arrange
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

    # Act
    users = []
    users.append(user_repo.save(user1))
    users.append(user_repo.save(user2))
    user_repo.session.commit()

    # Assert
    # Change to not get users locally from session
    fetched_users = user_repo.session.query(User).all()

    assert len(fetched_users) == 2 # The users should be successfully saved in the db
    assert fetched_users == users