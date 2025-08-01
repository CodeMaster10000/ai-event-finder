import logging
from functools import wraps
from typing import Union, Callable, Type


def log_calls(layer: str):
    """
    Decorator factory that logs method and function calls for a given logging layer.

    It wraps all public, class, and static methods of a class, as well as standalone functions.

    Args:
        layer (str): The logger name to use (e.g., "app.routes", "app.services").

    Returns:
        A decorator that can be applied to classes or functions.
    """
    def decorator(obj: Union[Type, Callable]) -> Union[Type, Callable]:
        """
        Class or function decorator that applies appropriate wrappers.

        Args:
            obj (type or function): The class or function to wrap.

        Returns:
            The wrapped class or function.
        """
        if isinstance(obj, type):
            cls_name = obj.__name__
            for name, attr in vars(obj).items():
                # skip dunder methods (including __init__)
                if name.startswith("__"):
                    continue

                # staticmethod
                if isinstance(attr, staticmethod):
                    func = attr.__func__
                    wrapped = _wrap_staticmethod(func, layer, cls_name, name)
                    setattr(obj, name, staticmethod(wrapped))

                # classmethod
                elif isinstance(attr, classmethod):
                    func = attr.__func__
                    wrapped = _wrap_classmethod(func, layer, cls_name, name)
                    setattr(obj, name, classmethod(wrapped))

                # plain method
                elif callable(attr):
                    wrapped = _wrap_method(attr, layer, cls_name, name)
                    setattr(obj, name, wrapped)

            return obj

        # Function decorator
        if callable(obj):
            return _wrap_function(obj, layer)

        return obj

    return decorator


def _wrap_method(method: Callable, layer: str, cls_name: str, method_name: str) -> Callable:
    """
    Wrap a class instance method to log on entry and exceptions.

    Args:
        method (Callable): The unbound instance method to wrap.
        layer (str): Logger name for emitting logs.
        cls_name (str): Name of the class containing the method.
        method_name (str): Name of the method to be wrapped.

    Returns:
        A wrapped method that logs calls and re-raises exceptions.
    """
    logger = logging.getLogger(layer)

    @wraps(method)
    def wrapped(self, *args, **kwargs):
        full = f"{cls_name}.{method_name}"
        logger.log(get_log_level(layer), f"{full}() called.")
        try:
            return method(self, *args, **kwargs)
        except Exception as e:
            logger.error(f"{full}() failed with {type(e).__name__}: {e}")
            raise

    return wrapped


def _wrap_classmethod(func: Callable, layer: str, cls_name: str, method_name: str) -> Callable:
    """
    Wrap a class method to log on entry and exceptions.

    Args:
        func (Callable): The original class method function.
        layer (str): Logger name for emitting logs.
        cls_name (str): Name of the class containing the method.
        method_name (str): Name of the method to be wrapped.

    Returns:
        A wrapped classmethod that logs calls and re-raises exceptions.
    """
    logger = logging.getLogger(layer)

    @wraps(func)
    def wrapped(cls, *args, **kwargs):
        full = f"{cls_name}.{method_name}"
        logger.log(get_log_level(layer), f"{full}() called.")
        try:
            return func(cls, *args, **kwargs)
        except Exception as e:
            logger.error(f"{full}() failed with {type(e).__name__}: {e}")
            raise

    return wrapped


def _wrap_staticmethod(func: Callable, layer: str, cls_name: str, method_name: str) -> Callable:
    """
    Wrap a static method to log on entry and exceptions.

    Args:
        func (Callable): The original static method function.
        layer (str): Logger name for emitting logs.
        cls_name (str): Name of the class containing the method.
        method_name (str): Name of the method to be wrapped.

    Returns:
        A wrapped function preserving staticmethod behavior.
    """
    logger = logging.getLogger(layer)

    @wraps(func)
    def wrapped(*args, **kwargs):
        full = f"{cls_name}.{method_name}"
        logger.log(get_log_level(layer), f"{full}() called.")
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{full}() failed with {type(e).__name__}: {e}")
            raise

    return wrapped


def _wrap_function(func: Callable, layer: str) -> Callable:
    """
    Wrap a free-standing function to log on entry and exceptions.

    Args:
        func (Callable): The function to wrap.
        layer (str): Logger name for emitting logs.

    Returns:
        A wrapped function that logs calls and re-raises exceptions.
    """
    logger = logging.getLogger(layer)

    @wraps(func)
    def wrapped(*args, **kwargs):
        name = func.__name__
        logger.log(get_log_level(layer), f"{name}() called.")
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{name}() failed with {type(e).__name__}: {e}")
            raise

    return wrapped


def get_log_level(layer: str) -> int:
    """
    Determine default logging level based on layer name.

    INFO if "route" or "service" appears in layer, otherwise DEBUG.

    Args:
        layer (str): The logger or layer identifier.

    Returns:
        int: logging.INFO or logging.DEBUG.
    """
    ll = layer.lower()
    if "route" in ll or "service" in ll:
        return logging.INFO
    return logging.DEBUG
