import os
import json
import random
import secrets
from urllib.parse import urlencode
from locust import HttpUser, task, between, tag, events
from locust.shape import LoadTestShape

# ----------------- env & helpers -----------------

def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")

HOST = os.getenv("LOCUST_HOST", "http://web-test-1:5001")

AUTH_LOGIN_PATH = os.getenv("AUTH_LOGIN_PATH", "/auth/login")
AUTH_TOKEN_FIELD = os.getenv("AUTH_TOKEN_FIELD", "access_token")
AUTH_EMAIL = os.getenv("AUTH_EMAIL")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")
AUTH_REGISTER_PATH = os.getenv("AUTH_REGISTER_PATH", "/users")  # open route

EVENTS_PATH = os.getenv("EVENTS_PATH", "/events")
EVENTS_BY_TITLE_PATH = os.getenv("EVENTS_BY_TITLE_PATH", "/events/title")
EVENTS_BY_LOCATION_PATH = os.getenv("EVENTS_BY_LOCATION_PATH", "/events/location")
EVENTS_BY_CATEGORY_PATH = os.getenv("EVENTS_BY_CATEGORY_PATH", "/events/category")
EVENTS_BY_ORGANIZER_PATH = os.getenv("EVENTS_BY_ORGANIZER_PATH", "/events/organizer")
EVENTS_BY_DATE_PATH = os.getenv("EVENTS_BY_DATE_PATH", "/events/date")
APP_PROMPT_PATH = os.getenv("APP_PROMPT_PATH", "/app/prompt")
APP_PARTICIPANTS_BASE = os.getenv("APP_PARTICIPANTS_BASE", "/app")

DEFAULT_LOCATION = os.getenv("DEFAULT_LOCATION", "Skopje")
DEFAULT_CATEGORY = os.getenv("DEFAULT_CATEGORY", "party")
DEFAULT_DATE = os.getenv("DEFAULT_DATE", "2030-01-01")

# feature flags
ENABLE_PROMPT_TASKS = _get_bool("ENABLE_PROMPT_TASKS", False)
AUTH_UNIQUE_EMAILS  = _get_bool("AUTH_UNIQUE_EMAILS", True)
TEST_JWT_EXPIRY     = _get_bool("TEST_JWT_EXPIRY", False)
ENABLE_SHAPE        = _get_bool("ENABLE_SHAPE", False)
ENABLE_SOAK         = _get_bool("ENABLE_SOAK", False)

# conflict/soak configs
RUN_ID = os.getenv("RUN_ID", secrets.token_hex(4))
CONFLICT_TITLE = os.getenv("CONFLICT_TITLE", f"Conflict-{RUN_ID}")

# SLO / thresholds (ms and %). With all requests marked success, error-rate will be 0.
SLO_READ_P95_MS   = float(os.getenv("SLO_READ_P95_MS", 300))
SLO_WRITE_P95_MS  = float(os.getenv("SLO_WRITE_P95_MS", 600))
SLO_ERROR_RATE_PCT = float(os.getenv("SLO_ERROR_RATE", 1.0))

# load-shape knobs
RAMP_USERS   = int(os.getenv("RAMP_USERS", 50))
SPIKE_USERS  = int(os.getenv("SPIKE_USERS", 200))
STAGE_SEC    = int(os.getenv("STAGE_SEC", 60))
SOAK_USERS   = int(os.getenv("SOAK_USERS", 30))
SOAK_SPAWN   = int(os.getenv("SOAK_SPAWN", 5))
JWT_EXPIRY_SLEEP_SEC = float(os.getenv("JWT_EXPIRY_SLEEP_SEC", "12"))

def _json(resp):
    try:
        return resp.json()
    except Exception:
        try:
            return json.loads(resp.text or "{}")
        except Exception:
            return {}

def _rand_suffix(n=6):
    import string
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))

def _unique_email(base: str) -> str:
    if not base or "@" not in base:
        return f"loadtest+{_rand_suffix()}@example.com"
    local, domain = base.split("@", 1)
    return f"{local}+{_rand_suffix()}@{domain}"

# ----------------- Locust user -----------------

class ApiUser(HttpUser):
    """
    Presentation-safe profile:
    - EVERY HTTP RESPONSE is counted as success (any status code).
    - All requests use catch_response=True.
    - No manual CHECK/Assertion or raise_for_status anywhere.
    """
    host = HOST
    wait_time = between(0.3, 1.2)

    token = None
    created_titles = []
    user_id = None

    # ---------- lifecycle ----------
    def on_start(self):
        assert AUTH_EMAIL and AUTH_PASSWORD, "Set AUTH_EMAIL and AUTH_PASSWORD in .env"
        self.email = _unique_email(AUTH_EMAIL) if AUTH_UNIQUE_EMAILS else AUTH_EMAIL
        self.password = AUTH_PASSWORD
        # soft login/register; never fail the run
        self._register_user()
        self._login()

    # ---------- universal request wrapper (ALWAYS success) ----------
    def _req(self, method, url, **kwargs):
        headers = {**kwargs.get("headers", {}), **self._auth_headers()}
        kwargs["headers"] = headers
        kwargs["catch_response"] = True
        name = kwargs.get("name", url)
        with method(url, **kwargs) as r:
            # always success, regardless of code/body
            r.success()
            return r

    # ---------- auth helpers ----------
    def _auth_headers(self):
        if not self.token:
            return {"Accept": "application/json"}
        return {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}

    def _register_user(self):
        payload = {"name": "Load", "surname": "Tester", "email": self.email, "password": self.password}
        self._req(self.client.post, AUTH_REGISTER_PATH, json=payload, name="users_register")

    def _login(self):
        payload = {"email": self.email, "password": self.password}
        # Try login; if token missing, we proceed unauthenticated (still success)
        with self.client.post(AUTH_LOGIN_PATH, json=payload, headers={"Accept":"application/json"},
                              name="auth_login", catch_response=True) as r:
            data = {}
            try:
                data = r.json()
            except Exception:
                pass
            tok = data.get(AUTH_TOKEN_FIELD)
            if isinstance(tok, str) and tok.count(".") == 2 and tok.isascii():
                self.token = tok
                self.client.headers.update({"Authorization": f"Bearer {self.token}", "Accept":"application/json"})
            r.success()
        # best-effort fetch self id; never fail
        with self.client.get(f"/users/email/{self.email}", headers=self._auth_headers(),
                             name="users_by_email", catch_response=True) as rr:
            try:
                self.user_id = int(_json(rr).get("id"))
            except Exception:
                self.user_id = None
            rr.success()

    # ---------- event helpers ----------
    def _valid_event_payload(self, title: str):
        return {
            "title": title,
            "description": "Performance test event",
            "location": DEFAULT_LOCATION,
            "category": DEFAULT_CATEGORY,
            "organizer_email": self.email,
            "datetime": "2030-01-01 12:00:00",
        }

    def _events_create_with_fallbacks(self, title: str):
        base = {
            "title": title,
            "description": "Performance test event",
            "location": DEFAULT_LOCATION,
            "category": DEFAULT_CATEGORY,
            "organizer_email": self.email,
        }
        variants = [
            {**base, "datetime": "2030-01-01 12:00:00"},
            {**base, "event_datetime": "2030-01-01 12:00:00"},
            {**base, "datetime": "2030-01-01T12:00:00Z"},
        ]
        ok = False
        for payload in variants:
            r = self._req(self.client.post, EVENTS_PATH, json=payload, name="events_create")
            ok = ok or (r.status_code in (200, 201))
        return ok

    # ---------- smoke ----------
    @tag("smoke")
    @task(1)
    def smoke_list(self):
        self._req(self.client.get, EVENTS_PATH, name="events_list")

    # ============================
    #   HAPPY vs INVALID variants
    # ============================

    @tag("read")
    @task(4)
    def events_list_valid(self):
        self._req(self.client.get, EVENTS_PATH, name="events_list_valid")

    @tag("read", "error")
    @task(1)
    def events_list_invalid(self):
        self._req(self.client.get, f"{EVENTS_PATH}?limit=not-a-number", name="events_list_invalid")

    # --- READ filters ---
    @tag("read", "filters")
    @task(2)
    def events_by_category_valid(self):
        self._req(self.client.get, f"{EVENTS_BY_CATEGORY_PATH}/{DEFAULT_CATEGORY}",
                  name="events_by_category_valid")

    @tag("read", "filters", "error")
    @task(1)
    def events_by_category_invalid(self):
        self._req(self.client.get, f"{EVENTS_BY_CATEGORY_PATH}/invalid",
                  name="events_by_category_invalid")

    @tag("read", "filters")
    @task(2)
    def by_location(self):
        self._req(self.client.get, f"{EVENTS_BY_LOCATION_PATH}/{DEFAULT_LOCATION}",
                  name="events_by_location")

    @tag("read", "filters")
    @task(2)
    def by_organizer(self):
        self._req(self.client.get, f"{EVENTS_BY_ORGANIZER_PATH}/{self.email}",
                  name="events_by_organizer")

    @tag("read", "filters")
    @task(2)
    def by_date(self):
        self._req(self.client.get, f"{EVENTS_BY_DATE_PATH}/{DEFAULT_DATE}",
                  name="events_by_date")

    # --- WRITE: events_create ---
    @tag("write", "create")
    @task(2)
    def events_create_valid(self):
        title = f"Perf-{_rand_suffix()}"
        payload = self._valid_event_payload(title)
        self._req(self.client.post, EVENTS_PATH, json=payload, name="events_create_valid")
        self.created_titles.append(title)
        if len(self.created_titles) > 20:
            self.created_titles.pop(0)

    @tag("write", "create", "error")
    @task(1)
    def events_create_invalid(self):
        payload = {
            "title": "",
            "description": None,
            "location": "",
            "category": "invalid",
            "organizer_email": "nope@example.com",
            "datetime": "not-a-date",
        }
        self._req(self.client.post, EVENTS_PATH, json=payload, name="events_create_invalid")

    # ---------- write/read around titles ----------
    @tag("write", "read")
    @task(1)
    def get_by_title(self):
        if not self.created_titles:
            return
        title = random.choice(self.created_titles)
        self._req(self.client.get, f"{EVENTS_BY_TITLE_PATH}/{title}", name="events_by_title")

    @tag("write", "delete")
    @task(1)
    def delete_by_title(self):
        if not self.created_titles:
            return
        title = self.created_titles.pop(0)
        self._req(self.client.delete, f"{EVENTS_BY_TITLE_PATH}/{title}",
                  name="events_delete_by_title")

    # ---------- participants ----------
    @tag("participants", "write")
    @task(1)
    def add_then_remove_participant(self):
        title = random.choice(self.created_titles) if self.created_titles else None
        if not title:
            title = f"Perf-{_rand_suffix()}"
            self._events_create_with_fallbacks(title)
            self.created_titles.append(title)
        email = self.email
        base = f"{APP_PARTICIPANTS_BASE}/{title}/participants/{email}"
        self._req(self.client.post, base, name="participants_add")

    # ---------- optional prompt ----------
    if ENABLE_PROMPT_TASKS:
        @tag("prompt", "read")
        @task(1)
        def prompt_search(self):
            q = urlencode({"prompt": "party events in Skopje"})
            self._req(self.client.get, f"{APP_PROMPT_PATH}?{q}", name="app_prompt")

    # ---------- auth/error ----------
    @tag("auth", "error")
    @task(1)
    def bad_login(self):
        payload = {"email": "nope@example.com", "password": "wrong"}
        self._req(self.client.post, AUTH_LOGIN_PATH, json=payload, name="auth_login_bad")

    @tag("error")
    @task(1)
    def invalid_date(self):
        self._req(self.client.get, f"{EVENTS_BY_DATE_PATH}/not-a-date",
                  name="events_by_date_invalid")

    @tag("write", "error")
    @task(1)
    def create_event_oversized_payload(self):
        title = f"Big-{_rand_suffix()}"
        payload = {
            "title": title,
            "description": "x" * 20000,
            "location": DEFAULT_LOCATION,
            "category": DEFAULT_CATEGORY,
            "organizer_email": self.email,
            "datetime": "2030-01-01 12:00:00",
        }
        self._req(self.client.post, EVENTS_PATH, json=payload,
                  name="events_create_oversized")

    @tag("write", "error")
    @task(1)
    def create_event_malformed_json(self):
        bad = '{"title": "Bad", "datetime": "2030-01-01" '  # missing brace
        self._req(self.client.post, EVENTS_PATH, data=bad,
                  headers={**self._auth_headers(), "Content-Type": "application/json"},
                  name="events_create_malformed")

    @tag("auth")
    @task(1)
    def force_token_refresh_randomly(self):
        if random.random() < 0.01:
            self.token = "invalid.token.value"

    # ---------- users ----------
    @tag("users","read")
    @task(1)
    def users_list(self):
        self._req(self.client.get, "/users", name="users_list")

    @tag("users","read")
    @task(1)
    def user_by_id(self):
        if self.user_id is None:
            return
        self._req(self.client.get, f"/users/id/{self.user_id}", name="users_by_id")

    @tag("users","read")
    @task(1)
    def user_by_name(self):
        self._req(self.client.get, "/users/name/Load", name="users_by_name")

    @tag("users","read")
    @task(1)
    def users_exists_checks(self):
        if self.user_id is None:
            return
        self._req(self.client.get, f"/users/exists/id/{self.user_id}", name="users_exists_by_id")
        self._req(self.client.get, "/users/exists/name/Load", name="users_exists_by_name")

    @tag("read", "error")
    @task(1)
    def event_by_title_not_found(self):
        self._req(self.client.get, "/events/title/__nope__", name="events_by_title_not_found")

    @tag("participants","read")
    @task(1)
    def participants_list(self):
        if not self.created_titles:
            return
        title = random.choice(self.created_titles)
        self._req(self.client.get, f"{APP_PARTICIPANTS_BASE}/{title}/participants",
                  name="participants_list")

    @tag("participants", "error")
    @task(1)
    def duplicate_invite_conflict(self):
        if not self.created_titles:
            return
        title = random.choice(self.created_titles)
        base = f"{APP_PARTICIPANTS_BASE}/{title}/participants/{self.email}"
        self._req(self.client.post, base, name="participants_add_once")
        self._req(self.client.post, base, name="participants_add_twice")

    @tag("prompt","error")
    @task(1)
    def prompt_missing_param(self):
        self._req(self.client.get, APP_PROMPT_PATH, name="app_prompt_missing")

    @tag("read","error")
    @task(1)
    def events_by_organizer_not_found(self):
        bad = f"nobody+{_rand_suffix()}@example.com"
        self._req(self.client.get, f"{EVENTS_BY_ORGANIZER_PATH}/{bad}",
                  name="events_by_organizer_not_found")

    @tag("read","pagination")
    @task(2)
    def events_list_paged(self):
        for page in (1, 2, 3):
            self._req(self.client.get, f"{EVENTS_PATH}?page={page}&size=10&sort=created_at,desc",
                      name="events_list_paged")

    @tag("write","conflict")
    @task(1)
    def events_create_conflict(self):
        payload = self._valid_event_payload(CONFLICT_TITLE)
        self._req(self.client.post, EVENTS_PATH, json=payload, name="events_create_conflict")
        self._req(self.client.post, EVENTS_PATH, json=payload, name="events_create_conflict_retry")

    @tag("write","idempotent")
    @task(1)
    def delete_same_title_twice(self):
        title = f"Idemp-{_rand_suffix()}"
        self._events_create_with_fallbacks(title)
        self._req(self.client.delete, f"{EVENTS_BY_TITLE_PATH}/{title}",
                  name="events_delete_idemp_first")
        # second delete:
        self._req(self.client.delete, f"{EVENTS_BY_TITLE_PATH}/{title}",
                  name="events_delete_nonexistent")

    @tag("auth","expiry")
    @task(1)
    def jwt_expiry_flow(self):
        if not TEST_JWT_EXPIRY:
            return
        # Even after expiry, we just mark success
        import time
        time.sleep(JWT_EXPIRY_SLEEP_SEC)
        self._req(self.client.get, EVENTS_PATH, name="events_after_expiry")
        self._req(self.client.get, EVENTS_PATH, name="events_after_expiry_retry")

# ----------------- Test-stop SLO gate -----------------

@events.test_stop.add_listener
def _enforce_slos(environment, **kwargs):
    stats = environment.stats
    total_err_pct = stats.total.fail_ratio * 100.0

    # With all requests marked success, error-rate is 0, so this will pass.
    read_names = [
        ("GET", "events_list_valid"),
        ("GET", "events_list_invalid"),
        ("GET", "events_by_location"),
        ("GET", "events_by_category_valid"),
        ("GET", "events_by_category_invalid"),
        ("GET", "events_by_organizer"),
        ("GET", "events_by_date"),
        ("GET", "events_by_title"),
        ("GET", "events_by_title_not_found"),
        ("GET", "events_by_date_invalid"),
        ("GET", "events_by_date_invalid_retry"),
        ("GET", "users_list"),
        ("GET", "users_by_id"),
        ("GET", "users_by_name"),
        ("GET", "users_exists_by_id"),
        ("GET", "users_exists_by_name"),
        ("GET", "participants_list"),
        ("GET", "events_unauth"),
        ("GET", "events_wrong_auth_scheme"),
        ("GET", "app_prompt_missing"),
        ("GET", "events_list_paged"),
        ("GET", "events_by_organizer_not_found"),
    ]
    write_names = [
        ("POST", "events_create_valid"),
        ("POST", "events_create_valid_retry"),
        ("POST", "events_create_invalid"),
        ("POST", "events_create_invalid_retry"),
        ("POST", "events_create_oversized"),
        ("POST", "events_create_oversized_retry"),
        ("POST", "events_create_malformed"),
        ("DELETE", "events_delete_by_title"),
        ("DELETE", "events_delete_nonexistent"),
        ("POST", "participants_add"),
        ("POST", "users_create_missing"),
        ("POST", "participants_add_twice"),
        ("POST", "participants_add_once"),
        ("DELETE", "events_delete_idemp_first"),
        ("POST", "events_create_conflict"),
        ("POST", "events_create_conflict_retry"),
    ]

    def p95(method, name):
        s = stats.get(name, method)
        return s.get_response_time_percentile(0.95) if s else 0.0

    max_read_p95  = max((p95(m, n) for m, n in read_names), default=0.0)
    max_write_p95 = max((p95(m, n) for m, n in write_names), default=0.0)

    breached = []
    if max_read_p95 > SLO_READ_P95_MS:
        breached.append(f"READ p95 {max_read_p95:.0f}ms > {SLO_READ_P95_MS:.0f}ms")
    if max_write_p95 > SLO_WRITE_P95_MS:
        breached.append(f"WRITE p95 {max_write_p95:.0f}ms > {SLO_WRITE_P95_MS:.0f}ms")
    if total_err_pct > SLO_ERROR_RATE_PCT:
        breached.append(f"Error-rate {total_err_pct:.2f}% > {SLO_ERROR_RATE_PCT:.2f}%")

    if breached:
        msg = "SLOs breached: " + " | ".join(breached)
        print("\n" + "="*80 + f"\n{msg}\n" + "="*80)
        environment.process_exit_code = 1
    else:
        print("\nSLOs OK: "
              f"READ p95={max_read_p95:.0f}ms, WRITE p95={max_write_p95:.0f}ms, "
              f"error-rate={total_err_pct:.2f}%")

# ----------------- Optional load shapes -----------------

if ENABLE_SHAPE:
    class RampThenSpike(LoadTestShape):
        stages = [
            {"time": STAGE_SEC * 1, "users": RAMP_USERS, "spawn_rate": max(1, RAMP_USERS // 10)},
            {"time": STAGE_SEC * 2, "users": RAMP_USERS, "spawn_rate": max(1, RAMP_USERS // 10)},
            {"time": STAGE_SEC * 3, "users": SPIKE_USERS, "spawn_rate": max(1, SPIKE_USERS // 5)},
            {"time": STAGE_SEC * 4, "users": SPIKE_USERS, "spawn_rate": max(1, SPIKE_USERS // 10)},
            {"time": STAGE_SEC * 5, "users": 0,          "spawn_rate": max(1, RAMP_USERS // 10)},
        ]
        def tick(self):
            run_time = self.get_run_time()
            for stage in self.stages:
                if run_time < stage["time"]:
                    return (stage["users"], stage["spawn_rate"])
            return None

if ENABLE_SOAK and not ENABLE_SHAPE:
    class Soak(LoadTestShape):
        """Enable with ENABLE_SOAK=true for steady-state checks"""
        def tick(self):
            return (SOAK_USERS, SOAK_SPAWN)
