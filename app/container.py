from dependency_injector import containers, providers
from app.extensions import db
from app.repositories.user_repository import UserRepository


# from app.services.user_service import UserService
from app.services.user_service_impl import UserService

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
    user_repository = providers.Factory(
        UserRepository
    )

    # Services

    # Provide a factory for your UserService implementation
    user_service = providers.Factory(
        UserService,
        # session=db_session,            # if your constructor needs it
        # user_repo=user_repository      # or pass in a repo provider
    )
