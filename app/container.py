from dependency_injector import containers, providers

from app.extensions import db
from app.repositories.event_repository_impl import EventRepositoryImpl
from app.repositories.user_repository_impl import UserRepositoryImpl
from app.services.app_service_impl import AppServiceImpl
from app.services.event_service_impl import EventServiceImpl
from app.services.user_service_impl import UserServiceImpl


class Container(containers.DeclarativeContainer):
    # Automatically wire dependencies into your routes and services modules
    wiring_config = containers.WiringConfiguration(
        packages=["app.routes", "app.services"]
    )

    # Sessions are created and closed per HTTP request
    #db_session = providers.Singleton(lambda: db.session)

    # If you have a UserRepository, you could also do:
    # user_repository = providers.Factory(UserRepository, session=db_session)
    # Repositories
    user_repository = providers.Singleton(
        UserRepositoryImpl,
    )
    event_repository = providers.Singleton(
        EventRepositoryImpl,
    )

    # Services

    # Service provider
    user_service = providers.Singleton(
        UserServiceImpl,
        user_repository=user_repository
    )
    event_service = providers.Singleton(
        EventServiceImpl,
        event_repository=event_repository,
        user_repository=user_repository,
    )


    app_service = providers.Singleton(
        AppServiceImpl, user_repo=user_repository, event_repo=event_repository,
    )


