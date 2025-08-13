from datetime import datetime
from sqlalchemy import func, text, select, bindparam
from sqlalchemy.orm import Session
from pgvector.sqlalchemy import Vector
from app.repositories.event_repository import EventRepository
from typing import List, Optional, Sequence, cast
from app.models.event import Event
from app.extensions import db
from app.configuration.config import Config
class EventRepositoryImpl(EventRepository):

    def __init__(self, session: Session):
        super().__init__(session)

    def get_all(self) -> List[Event]:
        return self.session.query(Event).all()  # type: List[Event]

    def get_by_id(self, event_id: int) -> Optional[Event]:
        return self.session.get(Event, event_id)

    def get_by_title(self, title: str) -> Optional[Event]:
        return self.session.query(Event).filter_by(title=title).first()

    def get_by_organizer_id(self, organizer_id: int) -> List[Event]:
        return self.session.query(Event).filter_by(organizer_id=organizer_id).all()

    def get_by_date(self, date: datetime) -> List[Event]:
        return self.session.query(Event).filter(func.date(Event.datetime) == date.date()) \
            .order_by(Event.datetime.asc()).all()

    def get_by_location(self, location: str) -> List[Event]:
        return self.session.query(Event).filter_by(location=location).all()

    def get_by_category(self, category: str) -> List[Event]:
        return self.session.query(Event).filter_by(category=category).all()

    def search_by_embedding(self, query_vector: Sequence[float], k: int = 10,
                            probes: Optional[int] = 10, session: Session = db.session) -> list[Event]:
        vec = [float(x) for x in query_vector]

        if probes is not None:
            session.execute(text("SET LOCAL ivfflat.probes = :p"), {"p": probes})
        # Sorting events by cosine distance to our query
        stmt = select(Event).from_statement(
            text("""
                 SELECT e.*
                 FROM events e
                 WHERE e.embedding IS NOT NULL
                 ORDER BY e.embedding <=> :q 
                 LIMIT :k
                 """).bindparams(
                bindparam("q", value=vec, type_=Vector(Config.UNIFIED_VECTOR_DIM)),
                bindparam("k", value=int(k)),
            )
        )

        # IMPORTANT: .scalars().all() → List[Event]
        res = session.execute(stmt, {"q": vec, "k": int(k)}).scalars().all()
        return cast(list[Event], res)

    def delete_by_id(self, event_id: int) -> None:
        event = self.session.get(Event, event_id)
        if event:
            self.session.delete(event)
            self.session.commit()

    def delete_by_title(self, title: str) -> None:
        event = self.session.query(Event).filter_by(title=title).first()
        if event:
            self.session.delete(event)
            self.session.commit()

    def save(self, event: Event) -> Event:
        self.session.add(event)
        self.session.commit()
        return event

    def exists_by_id(self, event_id: int) -> bool:
        return self.session.get(Event, event_id) is not None

    def exists_by_title(self, title: str) -> bool:
        return self.session.query(Event).filter_by(title=title).first() is not None

    def exists_by_location(self, location: str) -> bool:
        return self.session.query(Event).filter_by(location=location).first() is not None

    def exists_by_category(self, category: str) -> bool:
        return self.session.query(Event).filter_by(category=category).first() is not None

    def exists_by_date(self, date: datetime) -> bool:
        return self.session.query(Event).filter(func.date(Event.datetime) == date.date()).first() is not None
