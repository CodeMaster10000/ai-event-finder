# Event Finder

A Flask-based backend for the **Event Finder** application, providing a RESTful API to manage users and events with full CRUD support,
authentication, dependency injection and AI support.

## Features

- **User Management**: Signup, login, logout, and profile retrieval
- **Event Management**: Create, list, retrieve, update, and delete events
- **Guest Invitations**: Add and remove guests from events
- **Authentication**: JWT-based guard for protected endpoints
- **Serialization**: Marshmallow schemas for clean request/response modeling
- **Dependency Injection**: `dependency-injector` for wiring controllers and services
- **AI Support**: `ollama` and `OpenAI` for dynamic event retrieval and embedding
## Technologies & Dependencies

- **Flask**: Web framework (3.1.0)
- **Flask-SQLAlchemy**: ORM integration (SQLAlchemy 2.0.40)
- **Flask-JWT-Extended**: JWT authentication (PyJWT 2.10.1)
- **Flask-Bcrypt**: Password hashing (bcrypt 4.3.0)
- **marshmallow** & **marshmallow-sqlalchemy**: Schema-based (de)serialization
- **dependency-injector**: Service and controller wiring
- **pgvector**: Vector extension for PostgreSQL, used for RAG
- **OpenAI** SDK for cloud embeddings and chat  
- **sentence-transformers** 4.1.0, **transformers** 4.52.3 & **torch** 2.7.0 for local embeddings  
- **Ollama** CLI for local LLM completions

## Example for env. File
# ---- Flask / App Config ----
FLASK_ENV=development
DB_NAME=event_database
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
HOST_DB_PORT=5432
DB_POOL_RECYCLE=1800
DB_POOL_PRE_PING=true

APP_PORT=5000
HOST_APP_PORT=5000

PROVIDER=local  # cloud | local

# ---- Ollama Config ----
OLLAMA_EMBEDDING_URL=http://localhost:11434
HOST_OLLAMA_PORT=11434
OLLAMA_PORT=11434
OLLAMA_EMBEDDING_MODEL=bge-large
OLLAMA_LLM_MODEL=llama3.1:8b

# ---- OpenAI Config ----
OPENAI_API_KEY=hard-coded-test-key
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
UNIFIED_VECTOR_DIM=1024

# ---- RAG Config ----
RAG_TOP_K=5

# ---- LLM Hyperparameters ----
OLLAMA_TEMPERATURE=0.3
OLLAMA_TOP_P=0.9
OLLAMA_TOP_K=30
OLLAMA_NUM_PREDICT=236
OLLAMA_SEED=42

DEFAULT_K_EVENTS=5

OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.2
OPENAI_P=0.7
OPENAI_FREQUENCY_PENALTY=0.2
OPENAI_PRESENCE_PENALTY=0.0
OPENAI_MAX_TOKENS=220

# ---- Auth / Registration ----
AUTH_LOGIN_PATH=/auth/login
AUTH_TOKEN_FIELD=access_token
AUTH_EMAIL=loadtest@example.com
AUTH_PASSWORD=Sup3rSecret1
DEFAULT_ORGANIZER_EMAIL=loadtest@example.com
AUTH_REGISTER_PATH=/users        # open route (no JWT); used only if login fails
ENABLE_PROMPT_TASKS=false

# ---- Core API Paths ----
EVENTS_PATH=/events
EVENTS_BY_TITLE_PATH=/events/title
EVENTS_BY_LOCATION_PATH=/events/location
EVENTS_BY_CATEGORY_PATH=/events/category
EVENTS_BY_ORGANIZER_PATH=/events/organizer
EVENTS_BY_DATE_PATH=/events/date
APP_PROMPT_PATH=/app/prompt
APP_PARTICIPANTS_BASE=/app

# ---- Defaults for Locust tasks ----
DEFAULT_LOCATION=Skopje
DEFAULT_CATEGORY=party
DEFAULT_ORGANIZER_EMAIL="${AUTH_EMAIL}"
DEFAULT_DATE=2030-01-01          # used by /events/date/<YYYY-MM-DD>

# ---- Locust Config ----
LOCUST_HOST=http://web:5000      # If running inside docker-compose

LOCUST_USERS=50
LOCUST_SPAWN_RATE=10
LOCUST_RUN_TIME=5m
LOCUST_HEADLESS_FLAG=
LOCUST_CSV_PREFIX=locust_report
LOCUST_LOGLEVEL=INFO
LOCUST_PORT_MAPPING=8089:8089

# ---- Locust SLO Thresholds ----
SLO_READ_P95_MS=300       # max allowed p95 latency (ms) for read endpoints
SLO_WRITE_P95_MS=600      # max allowed p95 latency (ms) for write endpoints
SLO_ERROR_RATE=1.0        # max allowed error % (e.g., 1.0 = 1%)

# ---- Optional Load Shape (Ramp + Spike) ----
ENABLE_SHAPE=false        # true to use RampThenSpike shape
RAMP_USERS=50             # plateau users before spike
SPIKE_USERS=200           # spike target users
STAGE_SEC=60              # seconds per stage

# ---- Seed Data ----
SEED_EVENTS_CSV=data/preprocessed_events.csv
SEED_USERS_COUNT=20


## Example for flaskenv. File
FLASK_APP=run.py
FLASK_ENV=development
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:${HOST_DB_PORT}/${DB_NAME}"

## Code Coverage
```shell
poetry lock
poetry install
poetry install --with testing
pytest --cov=app --cov-report=term-missing
```
- always stick to coverage **greater than 90%**

## Seeding data into db
```shell
flask seed users
flask seed events
flask seed clean 
```
