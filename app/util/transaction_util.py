# app/util/transaction_util.py

from functools import wraps
from time import sleep
from contextlib import nullcontext
from sqlalchemy.orm.exc import StaleDataError
from app.extensions import db
from app.error_handler.exceptions import ConcurrencyException


def _current_session():
    """Return the actual request-scoped Session behind Flask-SQLAlchemy's scoped proxy."""
    s = db.session
    return s() if callable(s) else s  # unwrap if it's a scoped_session


def retry_conflicts(max_retries: int = 3, backoff_sec: float = 0.1):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except ConcurrencyException:
                    _current_session().rollback()
                    if attempt == max_retries:
                        raise
                    sleep(backoff_sec * attempt)
        return wrapped
    return decorator


def transactional(fn):
    """
    REQUIRED propagation for SQLAlchemy 2.0:
      - If no active transaction on this request's Session, begin/commit/rollback here.
      - If already in a transaction, just join it (no begin/commit/rollback).
    """
    @wraps(fn)
    def wrapped(*args, **kwargs):
        session = _current_session()
        outermost = (session.get_transaction() is None)  # 2.0 API

        ctx = session.begin() if outermost else nullcontext()
        try:
            with ctx:
                return fn(*args, session=session, **kwargs)

        except StaleDataError as e:
            if outermost:
                session.rollback()
                raise ConcurrencyException("Resource was updated by another transaction.") from e
            raise

        except Exception:
            if outermost:
                session.rollback()
            raise
    return wrapped
