from functools import wraps
from time import sleep
from sqlalchemy.orm.exc import StaleDataError

from app.extensions import db
from app.error_handler.exceptions import ConcurrencyException

def retry_conflicts(max_retries: int = 3, backoff_sec: float = 0.1):
    """
    Decorator to retry a function on ConcurrencyException (optimistic lock failure).

    Args:
        max_retries (int): Maximum retry attempts before giving up.
        backoff_sec (float): Base seconds to wait before retry, multiplied by attempt number.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except ConcurrencyException:
                    # rollback the failed transaction before retrying
                    db.session.rollback()
                    if attempt == max_retries:
                        # re-raise last ConcurrencyException
                        raise
                    # exponential backoff
                    sleep(backoff_sec * attempt)
        return wrapped
    return decorator


def transactional(fn):
    """
    Decorator to wrap a function in a database transaction using the request-scoped session.
    It will commit on success or rollback on exception, converting StaleDataError into ConcurrencyException.
    """
    @wraps(fn)
    def wrapped(*args, **kwargs):
        session = db.session
        outermost = not session.in_transaction()  # True if no txn yet

        try:
            if outermost:
                # We are the outer boundary → start/commit/rollback here
                with session.begin():
                    return fn(*args, session=session, **kwargs)
            else:
                # A transaction already exists → just join it
                return fn(*args, session=session, **kwargs)

        except StaleDataError as e:
            # Only the outermost boundary should translate/rollback.
            if outermost:
                session.rollback()
                raise ConcurrencyException(
                    "Resource was updated by another transaction."
                ) from e
            # Inner calls just bubble up; outer layer handles it
            raise

        except Exception:
            # Only the outermost boundary should roll-back here.
            if outermost:
                session.rollback()
            raise
    return wrapped

