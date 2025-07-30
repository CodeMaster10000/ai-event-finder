from dependency_injector import containers, providers
from app.extensions import db
from app.repositories.user_repository import UserRepository


# from app.services.user_service import UserService


# Define a container class using DeclarativeContainer base class
class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["app.routes", "app.services"])

    db_session = providers.Singleton(lambda: db.session)

    # Repositories
    user_repository = providers.Factory(
        UserRepository
    )

    # Services

    # Define a factory for the UserService
    user_service = providers.Factory(
        # UserService
    )
