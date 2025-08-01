import logging
from functools import wraps
from typing import Union, Callable, Type

def log_calls(layer: str):
    """
    Decorator factory that logs entry/exit/exceptions for different layers.
    """
    def decorator(obj: Union[Type, Callable]) -> Union[Type, Callable]:
        if isinstance(obj, type):
            cls_name = obj.__name__
            for name, attr in vars(obj).items():
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


def get_log_level(layer: str):
    """
    Default log level: INFO for *route* or *service* layers, otherwise DEBUG.
    """
    ll = layer.lower()
    if "route" in ll or "service" in ll:
        return logging.INFO
    return logging.DEBUG
