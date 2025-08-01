from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.util.logging_util import log_calls

@log_calls("app.repositories")
class UserRepositoryImpl(UserRepository):
    def __init__(self, session: Session):
        super().__init__(session)
        self.session = session

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.query(User).get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        return self.session.query(User).filter_by(email=email).first()

    def get_by_name(self, name: str) -> Optional[User]:
        return self.session.query(User).filter_by(name=name).first()

    def get_all(self) -> List[User]:
        return self.session.query(User).all()

    def save(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        return user

    def delete_by_id(self, user_id: int) -> None:
        user = self.session.get(User, user_id)
        self.session.delete(user)
        self.session.commit()

    def exists_by_id(self, user_id: int) -> bool:
        user = self.session.query(User).get(user_id)
        return True if user else False

    def exists_by_name(self, name: str) -> bool:
        return self.session.query(User).filter_by(name=name).first() is not None
