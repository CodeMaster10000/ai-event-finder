# tests/test_database_concurrency.py
import concurrent.futures
from datetime import datetime, UTC
import asyncio
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from app import create_app
from app.extensions import db
from app.models.event import Event
from app.models.user import User
from app.util.transaction_util import transactional, retry_conflicts
from app.error_handler.exceptions import (
    ConcurrencyException,
    UserAlreadyInEventException,
)
from tests.util.util_test import test_cfg


@pytest.fixture(scope="session")
def app():
    app = create_app(test_cfg)
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()


@pytest.fixture(scope="session")
def engine(app):
    return db.engine


@pytest.fixture(autouse=True)
def clean_db(app):
    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture(scope="function")
def Session(engine):
    return sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def clean_db(app):
    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


def test_db_two_sessions_conflict_raises_staledataerror(Session):
    s0 = Session()
    u = User(name="A", surname="B", email="a@b.com", password="pw")
    s0.add(u)
    s0.commit()
    uid = u.id
    s0.close()

    s1 = Session()
    s2 = Session()

    u1 = s1.get(User, uid)
    u2 = s2.get(User, uid)

    u1.name = "first"
    s1.commit()
    s1.close()

    u2.name = "second"
    with pytest.raises(StaleDataError):
        s2.commit()
    s2.rollback()
    s2.close()


def test_service_level_decorator_converts_and_retries(app, Session):
    with app.app_context():
        base = User(name="X", surname="Y", email="x@y.com", password="pw")
        db.session.add(base)
        db.session.commit()
        uid = base.id

    calls = {"n": 0}

    @retry_conflicts(max_retries=2, backoff_sec=0)
    @transactional
    def update_name(new_name: str, session=None):
        calls["n"] += 1
        u = session.get(User, uid)

        if calls["n"] == 1:
            s2 = Session()
            u2 = s2.get(User, uid)
            u2.name = "external-bump"
            s2.commit()
            s2.close()

        u.name = new_name

    with app.app_context():
        update_name("final-name")
        fresh = db.session.get(User, uid)
        assert fresh.name == "final-name"
        assert calls["n"] == 2


def test_delete_vs_update_conflict_raises_staledataerror(Session):
    s0 = Session()
    u = User(name="Del", surname="U", email="del@u.com", password="pw")
    s0.add(u)
    s0.commit()
    uid = u.id
    s0.close()

    s1 = Session()
    s2 = Session()

    u1 = s1.get(User, uid)
    u2 = s2.get(User, uid)

    s1.delete(u1)
    s1.commit()
    s1.close()

    u2.name = "should-fail"
    with pytest.raises(StaleDataError):
        s2.commit()
    s2.rollback()
    s2.close()


def test_retry_exhaustion_bubbles_concurrency_exception(app, Session):
    with app.app_context():
        base = User(name="Retry", surname="X", email="retry@x.com", password="pw")
        db.session.add(base)
        db.session.commit()
        uid = base.id

    attempts = {"n": 0}

    @retry_conflicts(max_retries=2, backoff_sec=0)
    @transactional
    def update_always_conflict(session=None):
        attempts["n"] += 1
        u = session.get(User, uid)

        s2 = Session()
        u2 = s2.get(User, uid)
        u2.name = f"external-{attempts['n']}"
        s2.commit()
        s2.close()

        u.name = "txn-attempt"

    with app.app_context():
        with pytest.raises(ConcurrencyException):
            update_always_conflict()
        assert attempts["n"] == 2


def test_nested_transactional_maps_at_outermost(app):
    calls = {"inner": 0, "outer": 0}

    @transactional
    def inner(session=None):
        calls["inner"] += 1
        raise StaleDataError("forced-inner-stale")

    @retry_conflicts(max_retries=1, backoff_sec=0)
    @transactional
    def outer(session=None):
        calls["outer"] += 1
        inner()

    with app.app_context():
        with pytest.raises(ConcurrencyException):
            outer()
        assert calls["inner"] == 1 and calls["outer"] == 1


def test_request_scoped_db_session_identity_same(app):
    with app.test_request_context():
        s1 = db.session
        s2 = db.session
        assert s1 is s2
        s1_real = s1() if callable(s1) else s1
        s2_real = s2() if callable(s2) else s2
        assert s1_real is s2_real


def test_http_conflict_mapping_returns_409(app):
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


def test_split_phase_create_has_no_txn_during_external_call_and_toctou(app, Session):
    from app.services.event_service_impl import EventServiceImpl
    from app.repositories.event_repository_impl import EventRepositoryImpl
    from app.repositories.user_repository_impl import UserRepositoryImpl
    from app.error_handler.exceptions import EventAlreadyExistsException

    with app.app_context():
        organizer = User(name="Org", surname="One", email="org@x.com", password="pw")
        db.session.add(organizer)
        db.session.commit()

        class StubEmbed:
            async def create_embedding(self, payload):
                real = db.session() if callable(db.session) else db.session
                assert real.get_transaction() is None
                s2 = Session()
                e = Event(title="Clash", description="rival", organizer_id=organizer.id)
                e.datetime = datetime.now(UTC)
                s2.add(e)
                s2.commit()
                s2.close()
                return [0.1, 0.2, 0.3]

        svc = EventServiceImpl(EventRepositoryImpl(), UserRepositoryImpl(), StubEmbed())

        data = {"title": "Clash", "description": "d", "organizer_email": "org@x.com"}
        with pytest.raises(EventAlreadyExistsException):
            asyncio.run(svc.create(data))


def test_transactional_joins_outer_and_rolls_back_once(app):
    @transactional
    def inner_create_user(email: str, session=None):
        session.add(User(name="Inner", surname="X", email=email, password="pw"))

    @transactional
    def outer_wrapper(session=None):
        inner_create_user("join@test.com")
        raise RuntimeError("boom")

    with app.app_context():
        with pytest.raises(RuntimeError):
            outer_wrapper()
        assert db.session.query(User).filter_by(email="join@test.com").count() == 0


def test_retry_conflicts_rolls_back_between_attempts(app):
    calls = {"n": 0}

    @retry_conflicts(max_retries=2, backoff_sec=0)
    @transactional
    def do_work(session=None):
        calls["n"] += 1
        if calls["n"] == 1:
            session.add(User(name="Temp", surname="T", email="temp@x.com", password="pw"))
            raise ConcurrencyException("simulate-concurrency")
        assert session.query(User).filter_by(email="temp@x.com").count() == 0
        session.add(User(name="OK", surname="Y", email="ok@x.com", password="pw"))

    with app.app_context():
        do_work()
        assert db.session.query(User).filter_by(email="ok@x.com").count() == 1


def test_request_session_isolation_across_requests(app):
    email = "iso@x.com"

    with app.test_request_context():
        real = db.session() if callable(db.session) else db.session
        with real.begin_nested() as sp:
            db.session.add(User(name="Iso", surname="L", email=email, password="pw"))
            db.session.flush()
            assert db.session.query(User).filter_by(email=email).count() == 1
            sp.rollback()
        assert db.session.query(User).filter_by(email=email).count() == 0

    with app.test_request_context():
        assert db.session.query(User).filter_by(email=email).count() == 0


def _session_id_for_request(app, name):
    with app.test_request_context():
        session = db.session()
        u = User(name=name, surname="X", email=f"{name}@test.com", password="pw")
        session.add(u)
        session.flush()
        return id(session)


def test_parallel_request_scoped_sessions_are_different(app):
    names = ["req1", "req2", "req3", "req4"]

    with app.app_context():
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(names)) as executor:
            results = list(executor.map(lambda n: _session_id_for_request(app, n), names))

    assert len(set(results)) == len(results)


def test_app_service_duplicate_invite_mapping_branch(app, monkeypatch):
    from app.services.app_service_impl import AppServiceImpl, UniqueViolation
    from app.repositories.user_repository_impl import UserRepositoryImpl
    from app.repositories.event_repository_impl import EventRepositoryImpl

    with app.app_context():
        u = User(name="U", surname="V", email="u@v.com", password="pw")
        db.session.add(u)
        db.session.commit()

        e = Event(title="E", description="d", organizer_id=u.id)
        e.datetime = datetime.now(UTC)
        db.session.add(e)
        db.session.commit()

        svc = AppServiceImpl(UserRepositoryImpl(), EventRepositoryImpl())

        def fake_save_raises(*args, **kwargs):
            raise IntegrityError("insert into guest_list ...", {}, UniqueViolation())

        monkeypatch.setattr(svc.event_repo, "save", fake_save_raises)

        with pytest.raises(UserAlreadyInEventException):
            svc.add_participant_to_event("E", "u@v.com")
