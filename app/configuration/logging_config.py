# app/configuration/logging_config.py
"""
Centralized logging configuration for the Flask app, plus
a decorator to auto-log method and function calls.
"""
import logging
from flask.logging import default_handler
from functools import wraps


def configure_logging(app):
    """
    Configure Flask’s built-in logger to emit to the console and
    apply INFO/INFO/DEBUG levels for API, Service and Repo Layers.

    Args:
        app (Flask): the application instance to configure logging on.
    """
    # 1) Remove stock Flask handler
    app.logger.handlers[:] = [
        h for h in app.logger.handlers
        if not isinstance(h, logging.StreamHandler)
    ]

    # 2) Parent logger accepts everything
    app.logger.setLevel(logging.DEBUG)

    # 3) Single console handler for all logs
    console_h = logging.StreamHandler()
    console_h.setLevel(logging.DEBUG)
    console_h.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-5s %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    ))
    app.logger.addHandler(console_h)

    # 4) Threshold each logical layer
    #      └─ matches folder names under app/
    app.logger.getChild("routes")       .setLevel(logging.INFO)
    app.logger.getChild("services")     .setLevel(logging.INFO)
    app.logger.getChild("repositories") .setLevel(logging.DEBUG)

    # 5) (Optional) quiet down Werkzeug’s default logging
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def log_calls(layer: str):
    """
    Decorator factory that logs entry/exit/exceptions for both
    functions and class methods, at INFO for API/Service and DEBUG for Repo.

    Usage on a function:
        @log_calls("routes.user_route")
        def list_users(...): ...

    Usage on a class:
        @log_calls("services.user_service_impl")
        class UserServiceImpl:
            def get_by_id(...): ...
    """
    def decorator(obj):
        # If decorating a class, wrap each of its public methods
        if isinstance(obj, type):
            for name, method in vars(obj).items():
                if callable(method) and not name.startswith("_"):
                    setattr(obj, name, _wrap(method, layer))
            return obj

        # Otherwise, assume a standalone function
        if callable(obj):
            return _wrap(obj, layer)

        # Fallback: return original
        return obj

    return decorator


def _wrap(fn, layer: str):
    """
    Internal helper to wrap a single function or method.
    Logs at DEBUG if layer starts with "repositories", else INFO.
    """
    level = logging.DEBUG if layer.startswith("repositories") else logging.INFO
    logger = logging.getLogger(f"app.{layer}")

    @wraps(fn)
    def wrapped(*args, **kwargs):
        logger.log(level,   f"Enter  {fn.__qualname__} args={args}, kwargs={kwargs}")
        try:
            result = fn(*args, **kwargs)
            #logger.log(level, f"Exit   {fn.__qualname__} returned={result!r}")
            return result
        except Exception:
            logger.exception(f"Exception in {fn.__qualname__}")
            raise

    return wrapped
