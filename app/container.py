from dependency_injector import containers, providers
from openai import AsyncOpenAI

from app.configuration.config import Config
from app.repositories.event_repository_impl import EventRepositoryImpl
from app.repositories.user_repository_impl import UserRepositoryImpl
from app.services.app_service_impl import AppServiceImpl
from app.services.embedding_service.embedding_service_impl import EmbeddingServiceImpl
from app.services.event_service_impl import EventServiceImpl
from app.services.model.model_service_impl import ModelServiceImpl
from app.services.user_service_impl import UserServiceImpl


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["app.routes", "app.services"])


    # Repositories
    user_repository = providers.Singleton(
        UserRepositoryImpl,
    )
    event_repository = providers.Singleton(
        EventRepositoryImpl,
    )

    provider = Config.PROVIDER

    if provider == "cloud":
        openai_client = providers.Singleton(
            AsyncOpenAI,
            api_key=Config.OPENAI_API_KEY)
        chat_model = providers.Object(getattr(Config, "OPENAI_MODEL", "gpt-4o-mini"))
        embedding_model = providers.Object(getattr(Config, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"))

    else:
        openai_client = providers.Singleton(
            AsyncOpenAI,
            api_key=Config.DMR_API_KEY,
            base_url=Config.DMR_BASE_URL,
        )
        chat_model = providers.Object(getattr(Config, "DMR_LLM_MODEL", "ai/llama3.1"))
        embedding_model = providers.Object(getattr(Config, "DMR_EMBEDDING_MODEL", "ai/mxbai-embed-large"))

    embedding_service = providers.Singleton(
        EmbeddingServiceImpl,
        client=openai_client,
        model=embedding_model,
    )
    model_service = providers.Singleton(
        ModelServiceImpl,
        event_repository=event_repository,
        embedding_service=embedding_service,
        client=openai_client,
        model=chat_model,
    )

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


