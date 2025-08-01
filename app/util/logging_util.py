import logging
from functools import wraps
from typing import Union, Callable, Type

def log_calls(layer: str):
    """
    Decorator factory that logs entry/exit/exceptions for different layers.

    Args:
        layer: The layer identifier (e.g., "app.routes", "app.services", "app.repositories")

    Usage:
        @log_calls("app.routes")
        @user_ns.route("")
        class UserBaseResource(Resource):

            ...

        @log_calls("app.services")
        def some_function():
            ...
    """

    def decorator(obj: Union[Type, Callable]) -> Union[Type, Callable]:
        # Class decorator: wrap each public method
        if isinstance(obj, type):
            for name, attr in vars(obj).items():
                if callable(attr) and not name.startswith("_"):
                    setattr(obj, name, _wrap_method(attr, layer, name))
            return obj

        # Function decorator
        if callable(obj):
            return _wrap_function(obj, layer)

        return obj

    return decorator


def _wrap_method(method: Callable, layer: str, method_name: str) -> Callable:
    """
    Internal helper: wraps a class method, logs on entry.
    """
    logger = logging.getLogger(layer)

    @wraps(method)
    def wrapped(self, *args, **kwargs):
        class_name = self.__class__.__name__
        full_method_name = f"{class_name}.{method_name}"
        level = get_log_level(layer)
        logger.log(level, f"{full_method_name}() called.")

        try:
            result = method(self, *args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"{full_method_name}() failed with {type(e).__name__}: {str(e)}")
            raise

    return wrapped


def _wrap_function(func: Callable, layer: str) -> Callable:
    """
    Internal helper: wraps a function, logs on entry.
    """
    logger = logging.getLogger(layer)

    @wraps(func)
    def wrapped(*args, **kwargs):
        func_name = func.__name__

        level = get_log_level(layer)
        logger.log(level, f"{func_name}() called.")

        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"{func_name}() failed with {type(e).__name__}: {str(e)}")
            raise

    return wrapped


def get_log_level(layer: str):
    """
    Pick a default log level based on the layer name.

    - if "route" in layer   → INFO
    - if "service" in layer → INFO
    - otherwise             → DEBUG
    """
    layer_lower = layer.lower()
    if "route" in layer_lower or "service" in layer_lower:
        return logging.INFO
    return logging.DEBUG