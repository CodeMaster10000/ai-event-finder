import os

from dependency_injector import containers, providers

from app.extensions import db
from app.repositories.event_repository_impl import EventRepositoryImpl
from app.repositories.user_repository_impl import UserRepositoryImpl
from app.services.app_service_impl import AppServiceImpl
from app.services.event_service_impl import EventServiceImpl
from app.services.user_service_impl import UserServiceImpl
from app.services.embedding_service.cloud_embedding_service import CloudEmbeddingService
from app.services.embedding_service.local_embedding_service import LocalEmbeddingService


class Container(containers.DeclarativeContainer):
    # Automatically wire dependencies into your routes and services modules
    wiring_config = containers.WiringConfiguration(
        packages=["app.routes", "app.services"]
    )

    # Provide a singleton SQLAlchemy session
    db_session = providers.Singleton(lambda: db.session)

    # If you have a UserRepository, you could also do:
    # user_repository = providers.Factory(UserRepository, session=db_session)
    # Repositories
    user_repository = providers.Singleton(
        UserRepositoryImpl,
        session=db_session,
    )
    event_repository = providers.Singleton(
        EventRepositoryImpl,
        session=db_session,
    )

    # Services

    # Service provider
    user_service = providers.Singleton(
        UserServiceImpl,
        user_repository=user_repository
    )
    # Determine embedding provider before container definition
    _embedding_provider = os.getenv("EMBEDDING_PROVIDER", "local").lower()
    if _embedding_provider not in ("local", "cloud"):
        raise ValueError(f"Unknown EMBEDDING_PROVIDER: {_embedding_provider}")

    if _embedding_provider == "cloud":
        embedding_service = providers.Singleton(CloudEmbeddingService)
    else:
        embedding_service = providers.Singleton(LocalEmbeddingService)


    event_service = providers.Singleton(
        EventServiceImpl,
        event_repository=event_repository,
        user_repository=user_repository,
        embedding_service=embedding_service,
    )


    app_service = providers.Singleton(
        AppServiceImpl, user_repo=user_repository, event_repo=event_repository,
    )

