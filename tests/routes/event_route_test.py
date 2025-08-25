# tests/routes/test_event_route.py

import os
import pytest
import importlib.util
from datetime import datetime, timedelta
from sqlalchemy.orm import scoped_session, sessionmaker

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.event import Event
from app.repositories.event_repository_impl import EventRepositoryImpl
from app.configuration.config import Config

from flask_jwt_extended import create_access_token
from dependency_injector import providers


# ----------------- Test Config (real Postgres test DB) -----------------

test_cfg = {
    "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": (
        f"postgresql://{os.getenv('TEST_DB_USER')}:{os.getenv('TEST_DB_PASSWORD')}"
        f"@{os.getenv('TEST_DB_HOST')}:{os.getenv('TEST_DB_PORT')}/{os.getenv('TEST_DB_NAME')}"
    ),
    "JWT_SECRET_KEY": "test-secret-key",
}

def has_flask_async_support() -> bool:
    # Flask[async] depends on asgiref; presence is a good proxy
    return importlib.util.find_spec("asgiref") is not None


# ----------------- App & DB Fixtures -----------------

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
def client(app):
    return app.test_client()

@pytest.fixture
def auth_header(app):
    # IMPORTANT: identity must be a STRING for PyJWT (sub claim)
    with app.app_context():
        token = create_access_token(identity="1", additional_claims={"email": "tester@example.com"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def organizer_user(db_session):
    u = User(
        name="Org",
        surname="User",
        email="organizer@example.com",
        password="dummy-hash",
    )
    db_session.add(u)
    db_session.commit()
    return u

@pytest.fixture
def now():
    return datetime(2025, 1, 1, 10, 0, 0)

@pytest.fixture
def seed_events(db_session, organizer_user, now):
    repo = EventRepositoryImpl()
    dummy_vec = [0.0] * Config.UNIFIED_VECTOR_DIM
    data = [
        {"title": "Tech Conference 2025", "datetime": now + timedelta(days=5, hours=14),
         "description": "Annual tech", "location": "Berlin", "category": "Technology"},
        {"title": "Jazz Night Live", "datetime": now + timedelta(days=10, hours=20),
         "description": "Smooth jazz", "location": "Paris", "category": "Music"},
        {"title": "Startup Pitch", "datetime": now + timedelta(days=7, hours=9, minutes=30),
         "description": "Pitching", "location": "Amsterdam", "category": "Business"},
    ]
    out = []
    for e in data:
        ev = Event(
            title=e["title"],
            datetime=e["datetime"],
            description=e["description"],
            organizer_id=organizer_user.id,
            location=e["location"],
            category=e["category"],
            embedding=dummy_vec,
        )
        saved = repo.save(ev, db_session)
        db_session.commit()
        out.append(saved)
    return out


# ----------------- Fake Service (aligns with your route; async create/update) -----------------

class FakeUserService:
    def __init__(self, session):
        self.session = session

    def get_by_email(self, email: str):
        return self.session.query(User).filter_by(email=email).first()

class FakeEventService:
    def __init__(self, session):
        self.session = session
        self.repo = EventRepositoryImpl()
        self._dummy_vec = [0.0] * Config.UNIFIED_VECTOR_DIM

    # ---- sync getters used by routes ----
    def get_all(self):
        return self.repo.get_all(self.session)

    def get_by_title(self, title: str):
        return self.session.query(Event).filter_by(title=title).first()

    def delete_by_title(self, title: str):
        e = self.get_by_title(title)
        if e is None:
            return False
        self.session.delete(e)
        self.session.commit()
        return True

    def get_by_location(self, location: str):
        return self.session.query(Event).filter_by(location=location).all()

    def get_by_category(self, category: str):
        return self.session.query(Event).filter_by(category=category).all()

    def get_by_organizer(self, email: str):
        user = self.session.query(User).filter_by(email=email).first()
        if not user:
            return []
        return self.session.query(Event).filter_by(organizer_id=user.id).all()

    def get_by_date(self, date_obj: datetime):
        """Route passes a datetime at 00:00 for the day; include [day, day+1)."""
        return (
            self.session.query(Event)
            .filter(Event.datetime >= date_obj, Event.datetime < date_obj + timedelta(days=1))
            .order_by(Event.datetime.asc())
            .all()
        )

    # ---- async methods expected by your route ----
    async def create(self, data: dict):
        """data from schema.load: expects keys:
           title, description, datetime (str or datetime), location, category, organizer_email
        """
        from marshmallow import ValidationError

        # require keys
        required = ["title", "description", "datetime", "location", "category", "organizer_email"]
        missing = [k for k in required if data.get(k) in (None, "", [])]
        if missing:
            raise ValidationError({k: ["Missing data for required field."] for k in missing})

        # accept datetime either already parsed by schema OR as a string
        raw_dt = data["datetime"]
        if isinstance(raw_dt, datetime):
            dt = raw_dt
        else:
            try:
                dt = datetime.strptime(str(raw_dt), "%Y-%m-%d %H:%M:%S")
            except Exception:
                raise ValidationError({"datetime": ["Must be in 'YYYY-MM-DD HH:MM:SS' format."]})

        # organizer lookup
        user = self.session.query(User).filter_by(email=data["organizer_email"]).first()
        if not user:
            raise ValidationError({"organizer_email": ["Organizer not found."]})

        ev = Event(
            title=data["title"],
            description=data["description"],
            datetime=dt,
            organizer_id=user.id,
            location=data["location"],
            category=data["category"],
            embedding=self._dummy_vec,
        )
        saved = self.repo.save(ev, self.session)
        self.session.commit()
        return saved

    async def update(self, title: str, patch: dict):
        from marshmallow import ValidationError
        ev = self.get_by_title(title)
        if not ev:
            # Leave as ValidationError → 422 (unless you map NotFound to 404 later)
            raise ValidationError({"title": [f"Event '{title}' not found."]})

        allowed = {"description", "datetime", "location", "category"}
        unknown = [k for k in patch.keys() if k not in allowed]
        if unknown:
            # NOTE: route calls schema.load(partial=True) BEFORE this and will reject unknown fields,
            # returning 400 "No valid update fields provided". So tests should expect 400, not 422.
            raise ValidationError({k: ["Unknown field."] for k in unknown})

        if "datetime" in patch:
            raw_dt = patch["datetime"]
            if isinstance(raw_dt, datetime):
                ev.datetime = raw_dt
            else:
                try:
                    ev.datetime = datetime.strptime(str(raw_dt), "%Y-%m-%d %H:%M:%S")
                except Exception:
                    raise ValidationError({"datetime": ["Must be in 'YYYY-MM-DD HH:MM:SS' format."]})
        if "description" in patch:
            ev.description = patch["description"]
        if "location" in patch:
            ev.location = patch["location"]
        if "category" in patch:
            ev.category = patch["category"]

        self.session.add(ev)
        self.session.commit()
        return ev


# ----------------- DI Override + Re-wire (instance-based) -----------------

@pytest.fixture(autouse=True)
def _override_and_rewire(db_session):
    from app.container import Container as AppContainer
    container = AppContainer()
    container.init_resources()

    container.event_service.override(providers.Object(FakeEventService(db_session)))
    container.user_service.override(providers.Object(FakeUserService(db_session)))

    import app.routes.event_route as event_route_module
    container.wire(modules=[event_route_module])

    yield

    try:
        container.unwire()
    except Exception:
        pass
    try:
        container.event_service.reset_override()
    except Exception:
        pass
    try:
        container.user_service.reset_override()
    except Exception:
        pass


# ----------------- Tests -----------------

def test_get_all_events_empty(client, auth_header):
    res = client.get("/events", headers=auth_header)
    assert res.status_code == 200
    assert res.get_json() == []

def test_get_all_events_with_data(client, auth_header, seed_events):
    res = client.get("/events", headers=auth_header)
    assert res.status_code == 200
    titles = {e["title"] for e in res.get_json()}
    assert {"Tech Conference 2025", "Jazz Night Live", "Startup Pitch"}.issubset(titles)

def test_get_by_title_found(client, auth_header, seed_events):
    res = client.get("/events/title/Tech Conference 2025", headers=auth_header)
    assert res.status_code == 200
    body = res.get_json()
    assert body["title"] == "Tech Conference 2025"

def test_get_by_title_not_found_returns_empty_object(client, auth_header):
    # Route returns dump(None) -> {} (200)
    res = client.get("/events/title/Nope", headers=auth_header)
    assert res.status_code == 200
    assert res.get_json() == {}

def test_delete_by_title_success(client, auth_header, seed_events):
    res = client.delete("/events/title/Startup Pitch", headers=auth_header)
    assert res.status_code == 204
    # verify it's gone
    res2 = client.get("/events/title/Startup Pitch", headers=auth_header)
    assert res2.status_code == 200
    assert res2.get_json() == {}

def test_delete_by_title_not_found(client, auth_header):
    res = client.delete("/events/title/Unknown", headers=auth_header)
    assert res.status_code == 404

def test_get_by_location(client, auth_header, seed_events):
    res = client.get("/events/location/Paris", headers=auth_header)
    assert res.status_code == 200
    data = res.get_json()
    assert all(e["location"] == "Paris" for e in data)

def test_get_by_category(client, auth_header, seed_events):
    res = client.get("/events/category/Technology", headers=auth_header)
    assert res.status_code == 200
    data = res.get_json()
    assert all(e["category"] == "Technology" for e in data)

def test_get_by_organizer(client, auth_header, organizer_user, seed_events):
    res = client.get(f"/events/organizer/{organizer_user.email}", headers=auth_header)
    assert res.status_code == 200
    data = res.get_json()
    # all seeded events belong to organizer_user
    assert len(data) >= 3
    assert all("title" in e for e in data)

def test_get_by_date_ok(client, auth_header, seed_events):
    # FIX: use the exact date of a seeded event (avoid boundary issues at midnight)
    day = seed_events[0].datetime.strftime("%Y-%m-%d")
    res = client.get(f"/events/date/{day}", headers=auth_header)
    assert res.status_code == 200
    data = res.get_json()
    assert any(e["title"] == seed_events[0].title for e in data)

def test_get_by_date_invalid_format(client, auth_header):
    res = client.get("/events/date/2025_01_01", headers=auth_header)
    assert res.status_code == 400
    body = res.get_json()
    assert "Date must be in 'YYYY-MM-DD' format" in body.get("message", "") or "message" in body

# ----- POST (async) -----

@pytest.mark.skipif(not has_flask_async_support(), reason="Flask async extra not installed; POST route is async")
def test_post_event_success(client, auth_header, organizer_user):
    payload = {
        "title": "E2",
        "description": "desc2",
        "datetime": "2025-08-04 16:00:00",
        "location": "loc2",
        "category": "cat2",
        "organizer_email": organizer_user.email,
    }
    res = client.post("/events", json=payload, headers=auth_header)
    assert res.status_code == 201
    body = res.get_json()
    assert body["title"] == "E2"
    assert body["datetime"] == "2025-08-04 16:00:00"
    assert "id" not in body  # keep your API contract

@pytest.mark.skipif(not has_flask_async_support(), reason="Flask async extra not installed; POST route is async")
def test_post_event_missing_required_fields_returns_422(client, auth_header):
    res = client.post("/events", json={"title": "X"}, headers=auth_header)
    assert res.status_code == 422
    body = res.get_json()
    assert body is not None

@pytest.mark.skipif(not has_flask_async_support(), reason="Flask async extra not installed; POST route is async")
def test_post_event_invalid_datetime_returns_422(client, auth_header, organizer_user):
    payload = {
        "title": "BadDT",
        "description": "desc",
        "datetime": "not-a-date",
        "location": "loc",
        "category": "cat",
        "organizer_email": organizer_user.email,
    }
    res = client.post("/events", json=payload, headers=auth_header)
    assert res.status_code == 422

@pytest.mark.skipif(not has_flask_async_support(), reason="Flask async extra not installed; POST route is async")
def test_post_event_unknown_organizer_returns_422(client, auth_header):
    payload = {
        "title": "NoOrg",
        "description": "desc",
        "datetime": "2025-08-04 16:00:00",
        "location": "loc",
        "category": "cat",
        "organizer_email": "missing@example.com",
    }
    res = client.post("/events", json=payload, headers=auth_header)
    assert res.status_code == 422

# ----- PUT (async) -----

@pytest.mark.skipif(not has_flask_async_support(), reason="Flask async extra not installed; PUT route is async")
def test_put_update_success(client, auth_header, seed_events):
    payload = {"description": "updated", "location": "Skopje"}
    res = client.put("/events/title/Tech Conference 2025", json=payload, headers=auth_header)
    assert res.status_code == 200
    body = res.get_json()
    assert body["description"] == "updated"
    assert body["location"] == "Skopje"

@pytest.mark.skipif(not has_flask_async_support(), reason="Flask async extra not installed; PUT route is async")
def test_put_empty_patch_returns_400(client, auth_header):
    res = client.put("/events/title/Anything", json={}, headers=auth_header)
    assert res.status_code == 400

@pytest.mark.skipif(not has_flask_async_support(), reason="Flask async extra not installed; PUT route is async")
def test_put_unknown_fields_returns_400(client, auth_header, seed_events):
    # FIX: The route runs schema.load(partial=True) first; unknown fields are dropped → patch == {}
    # which triggers 400 "No valid update fields provided". Expect 400 (not 422).
    res = client.put("/events/title/Tech Conference 2025", json={"foo": "bar"}, headers=auth_header)
    assert res.status_code == 400

@pytest.mark.skipif(not has_flask_async_support(), reason="Flask async extra not installed; PUT route is async")
def test_put_invalid_datetime_returns_422(client, auth_header, seed_events):
    res = client.put("/events/title/Tech Conference 2025",
                     json={"datetime": "bad-dt"},
                     headers=auth_header)
    assert res.status_code == 422

@pytest.mark.skipif(not has_flask_async_support(), reason="Flask async extra not installed; PUT route is async")
def test_put_not_found_returns_422(client, auth_header):
    res = client.put("/events/title/NoSuch", json={"description": "x"}, headers=auth_header)
    # With current service raising ValidationError for not found, this is 422.
    # If you later map NotFound → 404, update this assertion.
    assert res.status_code == 422
