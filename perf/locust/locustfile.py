import os
import json
import random
import secrets
from urllib.parse import urlencode
from locust import HttpUser, task, between, tag, events
from locust.clients import HttpSession
from locust.shape import LoadTestShape

# ----------------- env & helpers -----------------

def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")

HOST = os.getenv("LOCUST_HOST", "http://localhost:5000")

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

# SLO / thresholds (ms and %). If exceeded, the run will exit non-zero in headless mode.
SLO_READ_P95_MS   = float(os.getenv("SLO_READ_P95_MS", 300))
SLO_WRITE_P95_MS  = float(os.getenv("SLO_WRITE_P95_MS", 600))
SLO_ERROR_RATE_PCT = float(os.getenv("SLO_ERROR_RATE", 1.0))

# load-shape knobs
RAMP_USERS   = int(os.getenv("RAMP_USERS", 50))
SPIKE_USERS  = int(os.getenv("SPIKE_USERS", 200))
STAGE_SEC    = int(os.getenv("STAGE_SEC", 60))  # duration per stage
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

def _is_list_payload(d):
    # Accept several common shapes for list endpoints, or a raw list
    return (isinstance(d, dict) and isinstance(d.get("items") or d.get("data") or d.get("results") or d.get("events"), list)) \
           or isinstance(d, list)

# ----------------- Locust user -----------------

class ApiUser(HttpUser):
    """
    Safer auth flow + broader backend coverage:
    - Strict token parse & validation (ASCII + 2 dots)
    - Retry once on 401 / JWT-ish 422
    - Users endpoints, unauthorized cases, not-found, participants list/dup invite,
      prompt missing param, organizer not found, pagination, conflict create, idempotency,
      optional JWT-expiry & soak testing.
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
        self._ensure_login()

    # ---------- auth helpers ----------
    def _ensure_login(self):
        if not self._login():
            self._register_user()
            if not self._login():
                raise RuntimeError("Login failed after register")

    def _register_user(self):
        payload = {
            "name": "Load",
            "surname": "Tester",
            "email": self.email,
            "password": self.password,
        }
        with self.client.post(
            AUTH_REGISTER_PATH,
            json=payload,
            name="users_register",
            catch_response=True
        ) as r:
            if r.status_code in (201, 200, 409):  # OK if already exists
                r.success()
            else:
                r.failure(f"Register failed: {r.status_code} {r.text[:200]}")

    def _login(self):
        payload = {"email": self.email, "password": self.password}
        with self.client.post(
            AUTH_LOGIN_PATH,
            json=payload,
            headers={"Accept": "application/json"},
            name="auth_login",
            catch_response=True
        ) as r:
            # Allow 404 for "user not found" style APIs
            if r.status_code == 404:
                r.success()
                return False
            if r.status_code == 401:
                r.failure(f"Login 401: {r.text[:200]}")
                return False
            if not r.ok:
                r.failure(f"Login HTTP {r.status_code}: {r.text[:200]}")
                return False

            try:
                data = r.json()
            except Exception:
                r.failure(f"non-JSON login response {r.status_code}: {r.text[:200]}")
                return False

            token = data.get(AUTH_TOKEN_FIELD)
            if not isinstance(token, str) or (token.count(".") != 2) or (not token.isascii()):
                r.failure(f"bad token format for field {AUTH_TOKEN_FIELD}: {repr(token)[:80]}")
                return False

            self.token = token
            self.client.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            })
            # fetch own id for user/id tests
            self._fetch_self_id()
            r.success()
            return True

    def _auth_headers(self):
        if not self.token:
            return {"Accept": "application/json"}
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    def _needs_token_refresh(self, resp):
        if resp.status_code in (401, 422):
            try:
                body = _json(resp)
                text = json.dumps(body).upper()
            except Exception:
                text = ""
            # catch common JWT error shapes/messages
            triggers = ("JWT", "TOKEN", "AUTHORIZATION", "SIGNATURE",
                        "EXPIRED", "SUBJECT", "CSRF", "DECODE", "INVALID")
            return any(t in text for t in triggers)
        return False

    def _retry_auth(self, method, url, **kwargs):
        headers = {**kwargs.get("headers", {}), **self._auth_headers()}
        kwargs["headers"] = headers
        resp = method(url, **kwargs)
        if self._needs_token_refresh(resp):
            self._ensure_login()
            kwargs["headers"] = {**kwargs.get("headers", {}), **self._auth_headers()}
            return method(url, **kwargs)
        return resp

    # ---------- user helpers ----------
    def _fetch_self_id(self):
        if self.user_id is not None:
            return
        r = self.client.get(f"/users/email/{self.email}",
                            headers=self._auth_headers(),
                            name="users_by_email")
        if r.ok:
            try:
                self.user_id = int(_json(r).get("id"))
            except Exception:
                self.user_id = None

    # ---------- event helpers ----------
    def _valid_event_payload(self, title: str):
        return {
            "title": title,
            "description": "Performance test event",
            "location": DEFAULT_LOCATION,
            "category": DEFAULT_CATEGORY,
            "organizer_email": self.email,
            "datetime": "2030-01-01 12:00:00",  # "%Y-%m-%d %H:%M:%S"
        }

    def _invalid_event_payload(self, title: str):
        return {
            "title": "",                               # invalid
            "description": None,                       # invalid
            "location": "",                            # invalid
            "category": "invalid",                     # invalid enum
            "organizer_email": "nope@example.com",     # likely invalid
            "datetime": "not-a-date",                  # invalid format
        }

    def _events_create_with_fallbacks(self, title: str):
        base = {
            "title": title,
            "description": "Performance test event",
            "location": DEFAULT_LOCATION,
            "category": DEFAULT_CATEGORY,
            "organizer_email": self.email,
        }
        dt1 = "2030-01-01 12:00:00"
        dt2 = "2030-01-01T12:00:00Z"

        variants = [
            {**base, "datetime": dt1},
            {**base, "event_datetime": dt1},
            {**base, "datetime": dt2},
        ]

        for i, payload in enumerate(variants):
            last_attempt = i == len(variants) - 1
            with self.client.post(
                EVENTS_PATH,
                json=payload,
                headers=self._auth_headers(),
                name="events_create",
                catch_response=True
            ) as r:
                if r.status_code == 401:
                    self._ensure_login()
                    r2 = self.client.post(
                        EVENTS_PATH,
                        json=payload,
                        headers=self._auth_headers(),
                        name="events_create_retry"
                    )
                    if r2.status_code in (200, 201):
                        r.success()
                        return True
                    r.failure(f"Unexpected after retry: {r2.status_code} {r2.text[:200]}")
                    return False

                if r.status_code in (200, 201):
                    r.success()
                    return True

                if r.status_code in (400, 422) and ("ValidationError" in r.text or "VALIDATION" in r.text.upper()):
                    if last_attempt:
                        r.failure(f"All variants rejected. Last response: {r.status_code} {r.text[:200]}")
                        return False
                    else:
                        r.success()
                        continue

                r.failure(f"Unexpected {r.status_code}: {r.text[:200]}")
                return False

        return False

    # ---------- smoke ----------
    @tag("smoke")
    @task(1)
    def smoke_list(self):
        self._retry_auth(self.client.get, EVENTS_PATH, headers=self._auth_headers(), name="events_list")

    # ============================
    #   HAPPY vs INVALID variants
    # ============================

    # --- READ: events_list ---
    @tag("read")
    @task(4)
    def events_list_valid(self):
        url = EVENTS_PATH
        with self.client.get(url, headers=self._auth_headers(), name="events_list_valid", catch_response=True) as r:
            if self._needs_token_refresh(r):
                self._ensure_login()
                r2 = self.client.get(url, headers=self._auth_headers(), name="events_list_valid_retry")
                if r2.status_code != 200:
                    r.failure(f"HTTP {r2.status_code}: {r2.text[:200]}")
                    return
                data = _json(r2)
                if not _is_list_payload(data):
                    r.failure(f"Expected list-like payload, got: {str(data)[:120]}")
                else:
                    r.success()
                return

            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}: {r.text[:200]}")
                return
            data = _json(r)
            if not _is_list_payload(data):
                r.failure(f"Expected list-like payload, got: {str(data)[:120]}")
            else:
                r.success()

    @tag("read", "error")
    @task(1)
    def events_list_invalid(self):
        url = f"{EVENTS_PATH}?limit=not-a-number"
        with self.client.get(url, headers=self._auth_headers(), name="events_list_invalid", catch_response=True) as r:
            if r.status_code in (422, 200):
                r.success()
            elif self._needs_token_refresh(r):
                self._ensure_login()
                r2 = self.client.get(url, headers=self._auth_headers(), name="events_list_invalid_retry")
                if r2.status_code in (422, 200):
                    r.success()
                else:
                    r.failure(f"Unexpected after retry: {r2.status_code}: {r2.text[:200]}")
            else:
                r.failure(f"Unexpected {r.status_code}: {r.text[:200]}")

    # --- READ: events_by_category ---
    @tag("read", "filters")
    @task(2)
    def events_by_category_valid(self):
        self._retry_auth(
            self.client.get,
            f"{EVENTS_BY_CATEGORY_PATH}/{DEFAULT_CATEGORY}",
            headers=self._auth_headers(),
            name="events_by_category_valid",
        )

    @tag("read", "filters", "error")
    @task(1)
    def events_by_category_invalid(self):
        url = f"{EVENTS_BY_CATEGORY_PATH}/invalid"
        with self.client.get(url, headers=self._auth_headers(), name="events_by_category_invalid", catch_response=True) as r:
            if r.status_code in (422, 200):
                r.success()
            elif self._needs_token_refresh(r):
                self._ensure_login()
                r2 = self.client.get(url, headers=self._auth_headers(), name="events_by_category_invalid_retry")
                if r2.status_code in (422, 200):
                    r.success()
                else:
                    r.failure(f"Unexpected after retry: {r2.status_code}: {r2.text[:200]}")
            else:
                r.failure(f"Unexpected {r.status_code}: {r.text[:200]}")

    # --- WRITE: events_create ---
    @tag("write", "create")
    @task(2)
    def events_create_valid(self):
        title = f"Perf-{_rand_suffix()}"
        payload = self._valid_event_payload(title)
        with self.client.post(
            EVENTS_PATH,
            json=payload,
            headers=self._auth_headers(),
            name="events_create_valid",
            catch_response=True
        ) as r:
            if r.status_code == 201:
                r.success()
                self.created_titles.append(title)
                if len(self.created_titles) > 20:
                    self.created_titles.pop(0)
            elif r.status_code == 401:
                self._ensure_login()
                r2 = self.client.post(
                    EVENTS_PATH, json=payload, headers=self._auth_headers(), name="events_create_valid_retry"
                )
                if r2.status_code == 201:
                    r.success()
                    self.created_titles.append(title)
                    if len(self.created_titles) > 20:
                        self.created_titles.pop(0)
                else:
                    r.failure(f"Unexpected after retry: {r2.status_code}: {r2.text[:200]}")
            else:
                r.failure(f"Unexpected {r.status_code}: {r.text[:200]}")

    @tag("write", "create", "error")
    @task(1)
    def events_create_invalid(self):
        title = f"Bad-{_rand_suffix()}"
        payload = self._invalid_event_payload(title)
        with self.client.post(
            EVENTS_PATH,
            json=payload,
            headers=self._auth_headers(),
            name="events_create_invalid",
            catch_response=True
        ) as r:
            if r.status_code == 422:
                r.success()
            elif r.status_code == 401:
                self._ensure_login()
                r2 = self.client.post(
                    EVENTS_PATH, json=payload, headers=self._auth_headers(), name="events_create_invalid_retry"
                )
                if r2.status_code == 422:
                    r.success()
                else:
                    r.failure(f"Unexpected after retry: {r2.status_code}: {r2.text[:200]}")
            else:
                r.failure(f"Unexpected {r.status_code}: {r.text[:200]}")

    # ---------- other reads ----------
    @tag("read", "filters")
    @task(2)
    def by_location(self):
        self._retry_auth(
            self.client.get,
            f"{EVENTS_BY_LOCATION_PATH}/{DEFAULT_LOCATION}",
            headers=self._auth_headers(),
            name="events_by_location",
        )

    @tag("read", "filters")
    @task(2)
    def by_organizer(self):
        self._retry_auth(
            self.client.get,
            f"{EVENTS_BY_ORGANIZER_PATH}/{self.email}",
            headers=self._auth_headers(),
            name="events_by_organizer",
        )

    @tag("read", "filters")
    @task(2)
    def by_date(self):
        url = f"{EVENTS_BY_DATE_PATH}/{DEFAULT_DATE}"
        # use catch_response so a transient 422 doesn't auto-fail
        with self.client.get(
                url,
                headers=self._auth_headers(),
                name="events_by_date",
                catch_response=True
        ) as r:
            if r.status_code == 200:
                r.success()
                return

            # if it looks like a JWT/authorization-shaped 422/401, re-login & retry once
            if self._needs_token_refresh(r):
                self._ensure_login()
                r2 = self.client.get(
                    url,
                    headers=self._auth_headers(),
                    name="events_by_date_retry"
                )
                if r2.status_code == 200:
                    r.success()
                else:
                    r.failure(f"HTTP {r2.status_code}: {r2.text[:200]}")
            else:
                r.failure(f"HTTP {r.status_code}: {r.text[:200]}")

    # ---------- write/read around titles ----------
    @tag("write", "read")
    @task(1)
    def get_by_title(self):
        if not self.created_titles:
            return
        title = random.choice(self.created_titles)
        self._retry_auth(
            self.client.get,
            f"{EVENTS_BY_TITLE_PATH}/{title}",
            headers=self._auth_headers(),
            name="events_by_title",
        )

    @tag("write", "delete")
    @task(1)
    def delete_by_title(self):
        if not self.created_titles:
            return
        title = self.created_titles.pop(0)
        self._retry_auth(
            self.client.delete,
            f"{EVENTS_BY_TITLE_PATH}/{title}",
            headers=self._auth_headers(),
            name="events_delete_by_title",
        )

    # ---------- participants ----------
    @tag("participants", "write")
    @task(1)
    def add_then_remove_participant(self):
        title = random.choice(self.created_titles) if self.created_titles else None
        if not title:
            title = f"Perf-{_rand_suffix()}"
            ok = self._events_create_with_fallbacks(title)
            if not ok:
                return
            self.created_titles.append(title)

        email = self.email
        base = f"{APP_PARTICIPANTS_BASE}/{title}/participants/{email}"

        # accept 200/201/204 as success, 409 means "already present" -> also fine
        with self.client.post(base, headers=self._auth_headers(),
                              name="participants_add", catch_response=True) as r:
            if r.status_code in (200, 201, 204, 409):
                r.success()
            elif r.status_code == 401:
                self._ensure_login()
                r2 = self.client.post(base, headers=self._auth_headers(),
                                      name="participants_add_retry")
                if r2.status_code in (200, 201, 204, 409):
                    r.success()
                else:
                    r.failure(f"Unexpected after retry: {r2.status_code}: {r2.text[:200]}")
            else:
                r.failure(f"Unexpected {r.status_code}: {r.text[:200]}")

        # always attempt to remove to keep state tidy
        self._retry_auth(self.client.delete, base, headers=self._auth_headers(),
                         name="participants_remove")

    # ---------- prompt (optional) ----------
    if ENABLE_PROMPT_TASKS:
        @tag("prompt", "read")
        @task(1)
        def prompt_search(self):
            q = urlencode({"prompt": "party events in Skopje"})
            self._retry_auth(
                self.client.get,
                f"{APP_PROMPT_PATH}?{q}",
                headers=self._auth_headers(),
                name="app_prompt",
            )

    # ---------- auth/error ----------
    @tag("auth", "error")
    @task(1)
    def bad_login(self):
        payload = {"email": "nope@example.com", "password": "wrong"}
        with self.client.post(AUTH_LOGIN_PATH, json=payload, name="auth_login_bad", catch_response=True) as r:
            if r.status_code in (401, 404):
                r.success()
            else:
                r.failure(f"Expected 401/404, got {r.status_code}: {r.text}")

    @tag("error")
    @task(1)
    def invalid_date(self):
        url = f"{EVENTS_BY_DATE_PATH}/not-a-date"
        with self.client.get(url, headers=self._auth_headers(), name="events_by_date_invalid",
                             catch_response=True) as r:
            if r.status_code == 400:
                r.success()
            elif r.status_code == 401:
                self._ensure_login()
                r2 = self.client.get(url, headers=self._auth_headers(), name="events_by_date_invalid_retry")
                if r2.status_code == 400:
                    r.success()
                else:
                    r.failure(f"Expected 400 after retry, got {r2.status_code}: {r2.text}")
            else:
                r.failure(f"Expected 400, got {r.status_code}: {r.text}")

    @tag("write", "error")
    @task(1)
    def create_event_oversized_payload(self):
        title = f"Big-{_rand_suffix()}"
        payload = {
            "title": title,
            "description": "x" * 20000,  # very large
            "location": DEFAULT_LOCATION,
            "category": DEFAULT_CATEGORY,
            "organizer_email": self.email,
            "datetime": "2030-01-01 12:00:00",
        }
        with self.client.post(
            EVENTS_PATH, json=payload, headers=self._auth_headers(),
            name="events_create_oversized", catch_response=True
        ) as r:
            if r.status_code in (201, 400, 413, 422):
                r.success()
            elif r.status_code == 401:
                self._ensure_login()
                r2 = self.client.post(EVENTS_PATH, json=payload, headers=self._auth_headers(), name="events_create_oversized_retry")
                if r2.status_code in (201, 400, 413, 422):
                    r.success()
                else:
                    r.failure(f"Unexpected after retry: {r2.status_code} {r2.text}")
            else:
                r.failure(f"Unexpected {r.status_code}: {r.text}")

    @tag("write", "error")
    @task(1)
    def create_event_malformed_json(self):
        bad = '{"title": "Bad", "datetime": "2030-01-01" '  # missing closing brace
        with self.client.post(
            EVENTS_PATH,
            data=bad,
            headers={**self._auth_headers(), "Content-Type": "application/json"},
            name="events_create_malformed",
            catch_response=True
        ) as r:
            if r.status_code in (400, 415, 422):
                r.success()
            else:
                r.failure(f"Expected 400/415/422 for malformed JSON, got {r.status_code}: {r.text}")

    @tag("auth")
    @task(1)
    def force_token_refresh_randomly(self):
        # Occasionally invalidate token to ensure retry logic is exercised under load
        if random.random() < 0.01:
            self.token = "invalid.token.value"

    # =========================
    #   NEW BACKEND COVERAGE
    # =========================

    # Users: reads
    @tag("users","read")
    @task(1)
    def users_list(self):
        self._retry_auth(self.client.get, "/users",
                         headers=self._auth_headers(),
                         name="users_list")

    @tag("users","read")
    @task(1)
    def user_by_id(self):
        if self.user_id is None:
            return
        self._retry_auth(self.client.get, f"/users/id/{self.user_id}",
                         headers=self._auth_headers(),
                         name="users_by_id")

    @tag("users","read")
    @task(1)
    def user_by_name(self):
        self._retry_auth(self.client.get, "/users/name/Load",
                         headers=self._auth_headers(),
                         name="users_by_name")

    @tag("users","read")
    @task(1)
    def users_exists_checks(self):
        if self.user_id is None:
            return
        self._retry_auth(self.client.get, f"/users/exists/id/{self.user_id}",
                         headers=self._auth_headers(),
                         name="users_exists_by_id")
        self._retry_auth(self.client.get, "/users/exists/name/Load",
                         headers=self._auth_headers(),
                         name="users_exists_by_name")

    # Users: create validation
    @tag("users","error")
    @task(1)
    def users_create_missing_fields(self):
        bad = {"name": "X", "surname": "Y"}  # no email/password
        with self.client.post("/users", json=bad, name="users_create_missing", catch_response=True) as r:
            if r.status_code in (400, 422):
                r.success()
            else:
                r.failure(f"Expected 400/422, got {r.status_code}: {r.text[:200]}")

    # Unauthorized / wrong scheme
    @tag("auth", "error")
    @task(1)
    def events_unauthorized(self):
        # Temporarily remove Authorization from this user's session
        saved = self.client.headers.pop("Authorization", None)
        try:
            with self.client.get("/events",
                                 headers={"Accept": "application/json"},
                                 name="events_unauth",
                                 catch_response=True) as r:
                if r.status_code == 401:
                    r.success()
                else:
                    r.failure(f"Expected 401 when unauthenticated, got {r.status_code}")
        finally:
            if saved is not None:
                self.client.headers["Authorization"] = saved

    @tag("auth","error")
    @task(1)
    def events_wrong_auth_scheme(self):
        with self.client.get("/events",
                             headers={"Authorization": f"Token {self.token}", "Accept": "application/json"},
                             name="events_wrong_auth_scheme", catch_response=True) as r:
            if r.status_code == 401:
                r.success()
            else:
                r.failure(f"Expected 401 for wrong scheme, got {r.status_code}")

    # Not found cases
    @tag("read", "error")
    @task(1)
    def event_by_title_not_found(self):
        url = "/events/title/__nope__"
        with self.client.get(
                url,
                headers=self._auth_headers(),
                name="events_by_title_not_found",
                catch_response=True
        ) as r:
            if r.status_code in (404, 400):  # 404 expected for missing title (400 if your validator maps it)
                r.success()
            elif self._needs_token_refresh(r):
                self._ensure_login()
                r2 = self.client.get(
                    url,
                    headers=self._auth_headers(),
                    name="events_by_title_not_found_retry"
                )
                if r2.status_code in (404, 400):
                    r.success()
                else:
                    r.failure(f"Expected 404/400, got {r2.status_code}: {r2.text[:200]}")
            else:
                r.failure(f"Expected 404/400, got {r.status_code}: {r.text[:200]}")

    # Participants: list + duplicate invite conflict
    @tag("participants","read")
    @task(1)
    def participants_list(self):
        if not self.created_titles:
            return
        title = random.choice(self.created_titles)
        self._retry_auth(self.client.get, f"{APP_PARTICIPANTS_BASE}/{title}/participants",
                         headers=self._auth_headers(),
                         name="participants_list")

    @tag("participants", "error")
    @task(1)
    def duplicate_invite_conflict(self):
        if not self.created_titles:
            return
        title = random.choice(self.created_titles)
        base = f"{APP_PARTICIPANTS_BASE}/{title}/participants/{self.email}"

        # first add: could be 200/201 if absent, 409 if already there
        with self.client.post(base, headers=self._auth_headers(),
                              name="participants_add_once", catch_response=True) as r1:
            if r1.status_code in (200, 201, 204, 409):
                r1.success()
            else:
                r1.failure(f"Unexpected on first add: {r1.status_code}: {r1.text[:200]}")
                return  # nothing more to do

        # second add should conflict
        with self.client.post(base, headers=self._auth_headers(),
                              name="participants_add_twice", catch_response=True) as r2:
            if r2.status_code in (400, 409):
                r2.success()
            else:
                r2.failure(f"Expected 400/409 on duplicate invite, got {r2.status_code}: {r2.text[:200]}")

        # cleanup so other tasks don't hit 409 unexpectedly
        self._retry_auth(self.client.delete, base, headers=self._auth_headers(),
                         name="participants_remove_after_conflict")

    # Prompt: missing param (400)
    @tag("prompt","error")
    @task(1)
    def prompt_missing_param(self):
        with self.client.get(APP_PROMPT_PATH, headers=self._auth_headers(), name="app_prompt_missing", catch_response=True) as r:
            if r.status_code == 400:
                r.success()
            else:
                r.failure(f"Expected 400 for missing prompt, got {r.status_code}: {r.text[:200]}")

    # Organizer not found
    @tag("read","error")
    @task(1)
    def events_by_organizer_not_found(self):
        bad = f"nobody+{_rand_suffix()}@example.com"
        with self.client.get(f"{EVENTS_BY_ORGANIZER_PATH}/{bad}", headers=self._auth_headers(),
                             name="events_by_organizer_not_found", catch_response=True) as r:
            if r.status_code in (404, 400):
                r.success()
            else:
                r.failure(f"Expected 404/400 for unknown organizer, got {r.status_code}: {r.text[:200]}")

    # Pagination & sorting
    @tag("read","pagination")
    @task(2)
    def events_list_paged(self):
        for page in (1, 2, 3):
            url = f"{EVENTS_PATH}?page={page}&size=10&sort=created_at,desc"
            r = self._retry_auth(self.client.get, url, headers=self._auth_headers(), name="events_list_paged")
            if r.status_code != 200:
                events.request.fire(request_type="CHECK", name="events_list_paged_check",
                                    response_time=0, response_length=0,
                                    exception=AssertionError(f"paged {r.status_code}: {r.text[:120]}"))
                return

    # Duplicate-create conflict (uniqueness/race)
    @tag("write","conflict")
    @task(1)
    def events_create_conflict(self):
        payload = self._valid_event_payload(CONFLICT_TITLE)
        with self.client.post(EVENTS_PATH, json=payload, headers=self._auth_headers(),
                              name="events_create_conflict", catch_response=True) as r:
            if r.status_code in (201, 409):
                r.success()
            elif r.status_code == 401:
                self._ensure_login()
                r2 = self.client.post(EVENTS_PATH, json=payload, headers=self._auth_headers(),
                                      name="events_create_conflict_retry")
                if r2.status_code in (201, 409):
                    r.success()
                else:
                    r.failure(f"retry {r2.status_code}: {r2.text[:200]}")
            else:
                r.failure(f"Unexpected {r.status_code}: {r.text[:200]}")

    # Idempotency (delete twice)
    @tag("write","idempotent")
    @task(1)
    def delete_same_title_twice(self):
        title = f"Idemp-{_rand_suffix()}"
        if self._events_create_with_fallbacks(title):
            self.client.delete(f"{EVENTS_BY_TITLE_PATH}/{title}", headers=self._auth_headers(),
                               name="events_delete_idemp_first")
            r = self.client.delete(f"{EVENTS_BY_TITLE_PATH}/{title}", headers=self._auth_headers(),
                                   name="events_delete_idemp_second")
            if r.status_code not in (204, 404):
                events.request.fire(request_type="CHECK", name="delete_idempotency",
                                    response_time=0, response_length=0,
                                    exception=AssertionError(f"Delete not idempotent, got {r.status_code}"))

    # JWT expiry flow (enable by TEST_JWT_EXPIRY=true and set very short expiry in server)
    @tag("auth","expiry")
    @task(1)
    def jwt_expiry_flow(self):
        if not TEST_JWT_EXPIRY:
            return
        self._ensure_login()
        import time
        time.sleep(JWT_EXPIRY_SLEEP_SEC)  # wait past server token expiry
        r = self.client.get(EVENTS_PATH, headers=self._auth_headers(), name="events_after_expiry")
        if r.status_code == 401:
            self._ensure_login()
            r2 = self.client.get(EVENTS_PATH, headers=self._auth_headers(), name="events_after_expiry_retry")
            if r2.status_code != 200:
                r2.raise_for_status()

# ----------------- Test-stop SLO gate -----------------

@events.test_stop.add_listener
def _enforce_slos(environment, **kwargs):
    """
    Fail the run (headless) if SLOs are breached:
      - Max p95 across READ endpoints > SLO_READ_P95_MS
      - Max p95 across WRITE endpoints > SLO_WRITE_P95_MS
      - Total error rate > SLO_ERROR_RATE_PCT
    """
    stats = environment.stats
    total_err_pct = stats.total.fail_ratio * 100.0

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
        ("DELETE", "participants_remove"),
        ("POST", "users_create_missing"),
        ("POST", "participants_add_twice"),
        ("POST", "participants_add_once"),
        ("DELETE", "events_delete_idemp_first"),
        ("DELETE", "events_delete_idemp_second"),
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
        """
        Enable with ENABLE_SHAPE=true
        Timeline (each STAGE_SEC seconds):
          0–1: ramp to RAMP_USERS
          1–2: hold RAMP_USERS
          2–3: spike to SPIKE_USERS
          3–4: hold SPIKE_USERS
          4–5: ramp down to 0
        """
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
