# Event Finder

A Flask-based backend for the **Event Finder** application, providing a RESTful API to manage users and events with full CRUD support, authentication, dependency injection, and AI support.

---

## Features

* **User Management**: Signup, login, logout, and profile retrieval
* **Event Management**: Create, list, retrieve, update, and delete events
* **Guest Invitations**: Add and remove guests from events
* **Authentication**: JWT-based guard for protected endpoints
* **Serialization**: Marshmallow schemas for clean request/response modeling
* **Dependency Injection**: `dependency-injector` for wiring controllers and services
* **AI Support**: `Ollama` and `OpenAI` for dynamic event retrieval and embeddings

---

## Technologies & Dependencies

* **Flask** (3.1.0)
* **Flask-SQLAlchemy** (SQLAlchemy 2.0.40)
* **Flask-JWT-Extended** (PyJWT 2.10.1)
* **Flask-Bcrypt** (bcrypt 4.3.0)
* **marshmallow** & **marshmallow-sqlalchemy**
* **dependency-injector**
* **pgvector** for PostgreSQL vector search
* **OpenAI** SDK for embeddings and chat
* **sentence-transformers** 4.1.0, **transformers** 4.52.3, **torch** 2.7.0 for local embeddings
* **Ollama** CLI for local LLM completions

---

## Environment Variables

### Example for Flask env / App Config

```dotenv
FLASK_ENV=development
FLASK_APP=run.py
APP_PORT=5000
HOST_APP_PORT=5000
```

### Database Config

```dotenv
DB_NAME=event_database
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
HOST_DB_PORT=5432
DB_POOL_RECYCLE=1800
DB_POOL_PRE_PING=true
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:${HOST_DB_PORT}/${DB_NAME}"
```

### Provider Selection

```dotenv
PROVIDER=local   # options: cloud | local
```

### Docker Model Runner (DMR) Config

```dotenv
DMR_BASE_URL=http://host.docker.internal:12434/engines/llama.cpp/v1
DMR_API_KEY=dmr
DMR_LLM_MODEL=ai/llama3.1:latest
DMR_EMBEDDING_MODEL=ai/mxbai-embed-large
```

### OpenAI Config

```dotenv
OPENAI_API_KEY=hard-coded-test-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
UNIFIED_VECTOR_DIM=1024

OPENAI_TEMPERATURE=0.2
OPENAI_P=0.7
OPENAI_FREQUENCY_PENALTY=0.2
OPENAI_PRESENCE_PENALTY=0.0
OPENAI_MAX_TOKENS=220

# Extractor hyperparameters
OPENAI_EXTRACT_TEMPERATURE=0
OPENAI_EXTRACT_P=1
OPENAI_EXTRACT_FREQUENCY_PENALTY=0
OPENAI_EXTRACT_PRESENCE_PENALTY=0
OPENAI_EXTRACT_MAX_TOKENS=6
MAX_HISTORY_IN_CONTEXT = 5
```

### Authentication / Registration

```dotenv
AUTH_LOGIN_PATH=/auth/login
AUTH_REGISTER_PATH=/users
AUTH_TOKEN_FIELD=access_token
AUTH_EMAIL=loadtest@example.com
AUTH_PASSWORD=Sup3rSecret1
DEFAULT_ORGANIZER_EMAIL=loadtest@example.com
ENABLE_PROMPT_TASKS=false
```

### API Routes

```dotenv
EVENTS_PATH=/events
EVENTS_BY_TITLE_PATH=/events/title
EVENTS_BY_LOCATION_PATH=/events/location
EVENTS_BY_CATEGORY_PATH=/events/category
EVENTS_BY_ORGANIZER_PATH=/events/organizer
EVENTS_BY_DATE_PATH=/events/date
APP_PROMPT_PATH=/app/prompt
APP_PARTICIPANTS_BASE=/app
```

### Defaults for Events & Tasks

```dotenv
DEFAULT_K_EVENTS=5
MAX_K_EVENTS=15

DEFAULT_LOCATION=Skopje
DEFAULT_CATEGORY=party
DEFAULT_DATE=2030-01-01
```

### Load Testing (Locust)

```dotenv
LOCUST_HOST=http://web:5000
LOCUST_USERS=50
LOCUST_SPAWN_RATE=10
LOCUST_RUN_TIME=5m
LOCUST_HEADLESS_FLAG=
LOCUST_CSV_PREFIX=locust_report
LOCUST_LOGLEVEL=INFO
LOCUST_PORT_MAPPING=8089:8089

# SLO Thresholds
SLO_READ_P95_MS=300
SLO_WRITE_P95_MS=600
SLO_ERROR_RATE=1.0

# Optional Load Shape
ENABLE_SHAPE=false
RAMP_USERS=50
SPIKE_USERS=200
STAGE_SEC=60
```
```bash
TEST_DB_USER=test_user
TEST_DB_PASSWORD=test_password
TEST_DB_HOST=localhost
TEST_DB_PORT=5433
TEST_DB_NAME=test_database
HOST_TEST_DB_PORT=5433
```


### Seed Data

```dotenv
SEED_EVENTS_CSV=data/preprocessed_events.csv
SEED_USERS_COUNT=20
```

---

## Docker Model Runner

To pull the required models to Docker Model Runner, follow these instructions:
1. Open Docker Desktop
2. Go to settings, beta features
3. Enable Docker Model Runner
4. Exit the settings menu and go to the Models tab on the left
5. Click Add Models and pull llama3.1 and mxbai-embed-large

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/event-finder.git
   cd event-finder
   ```

2. **Set up a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # on Linux/Mac
   .venv\Scripts\activate     # on Windows
   ```

3. **Install dependencies**

   ```bash
   poetry install
   ```

4. **Set up environment variables**
   Copy the example file and adjust values:

   ```bash
   cp .env.example .env
   ```

5. **Run database migrations**

   ```bash
   flask db upgrade
   ```

6. **(Optional) Seed the database with sample data**

   ```bash
   flask seed users
   flask seed events
   ```

7. **Start the application**

   ```bash
   flask run
   ```

   The API will be available at `http://localhost:5000`

---

## Testing & Code Coverage

```bash
poetry install --with testing
pytest --cov=app --cov-report=term-missing
```
> Always maintain test coverage **greater than 90%**

## Locust instructions
How to incorporate Locust:
 - docker-compose up 
 - http://localhost:8089/

