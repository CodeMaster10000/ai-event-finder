from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.util.logging_util import log_calls

@log_calls("app.repositories")
class UserRepositoryImpl(UserRepository):

    def get_by_id(self, user_id: int, session:Session) -> Optional[User]:
        return session.query(User).get(user_id)

    def get_by_email(self, email: str, session:Session) -> Optional[User]:
        return session.query(User).filter_by(email=email).first()

    def get_by_name(self, name: str, session:Session) -> Optional[User]:
        return session.query(User).filter_by(name=name).first()

    def get_all(self, session:Session) -> list[type[User]]:
        return session.query(User).all()

    def save(self, user: User, session:Session) -> User:
        session.add(user)
        #session.commit()
        return user

    def delete_by_id(self, user_id: int, session:Session) -> None:
        user = session.get(User, user_id)
        session.delete(user)
        #session.commit()

    def exists_by_id(self, user_id: int, session:Session) -> bool:
        user = session.query(User).get(user_id)
        return True if user else False

    def exists_by_name(self, name: str, session:Session) -> bool:
        return session.query(User).filter_by(name=name).first() is not None
