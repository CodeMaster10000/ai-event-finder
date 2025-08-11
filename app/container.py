import os
from dependency_injector import containers, providers
from openai import OpenAI

from app.configuration.config import Config
from app.extensions import db
from app.repositories.event_repository_impl import EventRepositoryImpl
from app.repositories.user_repository_impl import UserRepositoryImpl
from app.services.embedding_service.local_embedding_service import LocalEmbeddingService
from app.services.event_service_impl import EventServiceImpl
from app.services.user_service_impl import UserServiceImpl
from app.services.app_service_impl import AppServiceImpl
from app.services.embedding_service.cloud_embedding_service import CloudEmbeddingService


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["app.routes", "app.services"])

    db_session = providers.Singleton(lambda: db.session)

    user_repository = providers.Singleton(UserRepositoryImpl, session=db_session)
    event_repository = providers.Singleton(EventRepositoryImpl, session=db_session)

    provider = os.getenv("PROVIDER", "local").lower()

    if provider == "cloud":
        openai_client = providers.Singleton(OpenAI, api_key=Config.OPENAI_API_KEY)
        embedding_service = providers.Singleton(
            CloudEmbeddingService,
            client=openai_client,
        )
    else:
        embedding_service = providers.Singleton(LocalEmbeddingService)

    user_service = providers.Singleton(UserServiceImpl, user_repository=user_repository)

    # Inject embedder so events are embedded on create/update
    event_service = providers.Singleton(
        EventServiceImpl,
        event_repository=event_repository,
        user_repository=user_repository,
        embedding_service=embedding_service,
    )

    # Required by app.routes.app_route (guest list ops)
    app_service = providers.Singleton(
        AppServiceImpl,
        user_repo=user_repository,
        event_repo=event_repository,
    )