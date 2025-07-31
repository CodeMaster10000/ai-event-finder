from dependency_injector import containers, providers
from app.extensions import db
from app.repositories.user_repository import UserRepository
from app.services.user_service_impl import UserServiceImpl

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
        UserRepository
    )

    # Services

    # Provide a factory for your UserService implementation
    user_service = providers.Singleton(
        UserServiceImpl
    )
