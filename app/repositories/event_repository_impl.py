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

    def get_all(self, session:Session) -> list[type[Event]]:
        return session.query(Event).all()  # type: List[Event]

    def get_by_id(self, event_id: int, session:Session) -> Optional[Event]:
        return session.get(Event, event_id)

    def get_by_title(self, title: str, session:Session) -> Optional[Event]:
        return session.query(Event).filter_by(title=title).first()

    def get_by_organizer_id(self, organizer_id: int, session:Session) -> list[type[Event]]:
        return session.query(Event).filter_by(organizer_id=organizer_id).all()

    def get_by_date(self, date: datetime, session:Session) -> list[type[Event]]:
        return session.query(Event).filter(date.date() == func.date(Event.datetime)) \
            .order_by(Event.datetime.asc()).all()

    def get_by_location(self, location: str, session:Session) -> list[type[Event]]:
        return session.query(Event).filter_by(location=location).all()

    def get_by_category(self, category: str, session:Session) -> list[type[Event]]:
        return session.query(Event).filter_by(category=category).all()

    def delete_by_id(self, event_id: int, session:Session) -> None:
        event = session.get(Event, event_id)
        if event:
            session.delete(event)

    def search_by_embedding(self, session: Session, query_vector: Sequence[float],
                            k: int = Config.DEFAULT_K_EVENTS, probes: Optional[int] = 10) -> list[Event]:
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

    def delete_by_title(self, title: str, session:Session) -> None:
        event = session.query(Event).filter_by(title=title).first()
        if event:
            session.delete(event)

    def save(self, event: Event, session:Session) -> Event:
        session.add(event)
        return event

    def exists_by_id(self, event_id: int, session:Session) -> bool:
        return session.get(Event, event_id) is not None

    def exists_by_title(self, title: str, session:Session) -> bool:
        return session.query(Event).filter_by(title=title).first() is not None

    def exists_by_location(self, location: str, session:Session) -> bool:
        return session.query(Event).filter_by(location=location).first() is not None

    def exists_by_category(self, category: str, session:Session) -> bool:
        return session.query(Event).filter_by(category=category).first() is not None

    def exists_by_date(self, date: datetime, session:Session) -> bool:
        return session.query(Event).filter(date.date() == func.date(Event.datetime)).first() is not None
