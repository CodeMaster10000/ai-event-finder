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
FLASK_ENV=development
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
HOST_DB_PORT=5432
APP_PORT=5000
HOST_APP_PORT=5000
DB_NAME=event_database
OLLAMA_EMBEDDING_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_LLM=llama3.1:latest
VECTOR_DIM=768
EMBEDDING_PROVIDER=local [cloud | local]

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