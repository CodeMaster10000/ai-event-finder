from dependency_injector import containers, providers
from app.extensions import db
from app.services.user_service_impl import UserServiceImpl


# Define a container class using DeclarativeContainer base class
class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["app.routes", "app.services"])

    db_session = providers.Singleton(lambda: db.session)

    # Repositories
    # Services

    # Define a factory for the UserService
    user_service = providers.Factory(
        # UserService
    )
