from dependency_injector import containers, providers
from app.extensions import db
from app.repositories.user_repository import UserRepository
from app.services.user_service_impl import UserServiceImpl


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["app.routes", "app.services"])

    # Provide a singleton SQLAlchemy session
    db_session = providers.Singleton(lambda: db.session)

    # Repository provider
    user_repository = providers.Factory(
        UserRepository,
        session=db_session,            # inject the DB session into the repo
    )

    # Service provider
    user_service = providers.Factory(
        UserServiceImpl,
        user_repository=user_repository  # inject the repo into the service
    )
