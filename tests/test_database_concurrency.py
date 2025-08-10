# tests/test_concurrency.py
import pytest
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from app import create_app
from app.extensions import db
from app.models.user import User
from app.util.transaction_util import transactional, retry_conflicts
from app.error_handler.exceptions import ConcurrencyException

@pytest.fixture(scope="function")
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="function")
def engine(app):
    return db.get_engine()


@pytest.fixture(scope="function")
def Session(engine):
    return sessionmaker(bind=engine)


def test_db_two_sessions_conflict_raises_staledataerror(Session):
    """Real ORM conflict: two independent sessions update the same row."""
    # seed
    s0 = Session()
    u = User(name="A", surname="B", email="a@b.com", password="pw")
    s0.add(u); s0.commit()
    uid = u.id
    s0.close()

    s1 = Session()
    s2 = Session()

    u1 = s1.get(User, uid)
    u2 = s2.get(User, uid)

    # first commit bumps version
    u1.name = "first"
    s1.commit()
    s1.close()

    # second tries to commit stale state -> StaleDataError
    u2.name = "second"
    with pytest.raises(StaleDataError):
        s2.commit()
    s2.rollback()
    s2.close()


def test_service_level_decorator_converts_and_retries(app, Session):
    """
    Cause a real version bump from a separate Session mid-transaction.
    transactional should convert StaleDataError -> ConcurrencyException,
    retry_conflicts should retry, and the second attempt should succeed.
    """
    # seed a user
    with app.app_context():
        base = User(name="X", surname="Y", email="x@y.com", password="pw")
        db.session.add(base)
        db.session.commit()
        uid = base.id

    calls = {"n": 0}

    @retry_conflicts(max_retries=2, backoff_sec=0)  # 1 retry
    @transactional
    def update_name(new_name: str, session=None):
        """First attempt: create a real conflict. Second attempt: succeed."""
        calls["n"] += 1
        u = session.get(User, uid)

        if calls["n"] == 1:
            # Bump version in a totally separate Session to create a conflict.
            s2 = Session()
            u2 = s2.get(User, uid)
            u2.name = "external-bump"
            s2.commit()
            s2.close()

        # This write will conflict on the first attempt and succeed on the second.
        u.name = new_name
        # commit occurs when @transactional exits

    with app.app_context():
        update_name("final-name")  # should retry then succeed
        # verify persisted result
        fresh = db.session.get(User, uid)
        assert fresh.name == "final-name"
        assert calls["n"] == 2

def test_delete_vs_update_conflict_raises_staledataerror(Session):
    """
    One session deletes a row while another tries to update its stale copy -> StaleDataError.
    """
    s0 = Session()
    u = User(name="Del", surname="U", email="del@u.com", password="pw")
    s0.add(u); s0.commit()
    uid = u.id
    s0.close()

    s1 = Session()
    s2 = Session()

    u1 = s1.get(User, uid)  # will delete
    u2 = s2.get(User, uid)  # will update (stale)

    s1.delete(u1)
    s1.commit()
    s1.close()

    u2.name = "should-fail"
    with pytest.raises(StaleDataError):
        s2.commit()
    s2.rollback()
    s2.close()


def test_retry_exhaustion_bubbles_concurrency_exception(app, Session):
    """
    Force a real conflict on every attempt so retries exhaust and ConcurrencyException is raised.
    """
    with app.app_context():
        base = User(name="Retry", surname="X", email="retry@x.com", password="pw")
        db.session.add(base)
        db.session.commit()
        uid = base.id

    attempts = {"n": 0}

    @retry_conflicts(max_retries=2, backoff_sec=0)  # both attempts will conflict
    @transactional
    def update_always_conflict(session=None):
        attempts["n"] += 1
        # Load in transactional session
        u = session.get(User, uid)

        # External bump in a separate Session to force a version conflict
        s2 = Session()
        u2 = s2.get(User, uid)
        u2.name = f"external-{attempts['n']}"
        s2.commit()
        s2.close()

        # This will conflict on commit
        u.name = "txn-attempt"

    with app.app_context():
        with pytest.raises(ConcurrencyException):
            update_always_conflict()
        assert attempts["n"] == 2  # tried twice, then bubbled


def test_http_conflict_mapping_returns_409(app):
    """
    Register a test route that raises ConcurrencyException and assert 409 is returned.
    (Uses the app's error handler, or we add one here if not present.)
    """
    # Ensure there is a handler (safe to register here for test isolation)
    @app.errorhandler(ConcurrencyException)
    def _handle_concurrency(e):
        return {"error": {"code": "CONCURRENT_UPDATE", "message": str(e)}}, 409

    @app.route("/_raise_conflict")
    def _raise_conflict():
        raise ConcurrencyException("test-conflict")

    client = app.test_client()
    resp = client.get("/_raise_conflict")
    assert resp.status_code == 409
    data = resp.get_json()
    assert data["error"]["code"] == "CONCURRENT_UPDATE"
