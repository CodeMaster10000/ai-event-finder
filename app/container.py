from dependency_injector import containers, providers
from app.extensions import db

# import your repos and services
from app.repositories.user_repository_impl import UserRepositoryImpl
from app.services.user_service_impl import UserServiceImpl
from app.repositories.event_repository_impl import EventRepositoryImpl
from app.services.event_service_impl import EventServiceImpl

class Container(containers.DeclarativeContainer):
    # Automatically wire dependencies into your routes and services modules
    wiring_config = containers.WiringConfiguration(
        packages=["app.routes", "app.services"]
    )

    # Provide a singleton SQLAlchemy session
    db_session = providers.Singleton(lambda: db.session)

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
    user_service = providers.Singleton(
        UserServiceImpl,
        user_repository=user_repository,
    )
    event_service = providers.Singleton(
        EventServiceImpl,
        event_repository=event_repository,
        user_repository=user_repository,
    )

