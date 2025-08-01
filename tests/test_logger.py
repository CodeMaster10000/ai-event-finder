# tests/test_logging_all.py

import logging
import pytest

# ← adjust these to match your project structure:
from app.configuration.logging_config import configure_logging, LOGGING
from app.util.logging_util import log_calls, get_log_level


@pytest.fixture(autouse=True)
def reset_and_setup_logging():
    # 1) Tear down any existing loggers/handlers
    logging.shutdown()
    for name in list(logging.root.manager.loggerDict):
        logging.root.manager.loggerDict.pop(name)

    # 2) Apply your dictConfig
    configure_logging()

    yield

    # 3) Clean up again
    logging.shutdown()


def test_configure_logging_app_delegates_to_root():
    app_logger = logging.getLogger("app")
    # no handlers on "app"
    assert app_logger.handlers == []
    # should propagate up to root
    assert app_logger.propagate is True
    # configured level
    assert app_logger.level == logging.DEBUG


def test_configure_logging_other_loggers_and_root():
    # werkzeug stays at ERROR
    wk = logging.getLogger("werkzeug")
    assert wk.level == logging.ERROR

    # "app.routes" inherits NOTSET + propagate=True
    routes = logging.getLogger("app.routes")
    assert routes.level == logging.NOTSET
    assert routes.propagate is True
    assert routes.getEffectiveLevel() == logging.DEBUG

    # root logger remains WARNING with a StreamHandler
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)


def test_configure_logging_idempotent():
    before = list(logging.getLogger("app").handlers)
    configure_logging()
    after = list(logging.getLogger("app").handlers)
    # no duplicate handlers created
    assert before == after


def test_get_log_level_variants():
    # "route"/"service" → INFO; everything else → DEBUG
    assert get_log_level("app.routes") == logging.INFO
    assert get_log_level("order.service") == logging.INFO
    assert get_log_level("some.Services") == logging.INFO

    assert get_log_level("app.repositories") == logging.DEBUG
    assert get_log_level("custom.layer") == logging.DEBUG


def test_log_calls_wraps_free_function(caplog):
    caplog.set_level(logging.INFO, logger="app.services")

    @log_calls("app.services")
    def add(x, y):
        return x + y

    assert add(2, 3) == 5

    recs = [r for r in caplog.records if r.name == "app.services"]
    assert len(recs) == 1
    assert recs[0].levelno == logging.INFO
    assert recs[0].getMessage() == "add() called."


def test_log_calls_function_exception(caplog):
    # capture both INFO entry and ERROR exception
    caplog.set_level(logging.DEBUG, logger="app.services")

    @log_calls("app.services")
    def fail():
        raise ValueError("boom!")

    with pytest.raises(ValueError):
        fail()

    recs = [r for r in caplog.records if r.name == "app.services"]
    # entry log at INFO
    assert any(r.levelno == logging.INFO and "fail() called." in r.getMessage()
               for r in recs)
    # exception log at ERROR
    assert any(r.levelno == logging.ERROR and
               "fail() failed with ValueError: boom!" in r.getMessage()
               for r in recs)

def test_log_calls_wraps_all_class_methods(caplog):
    # capture DEBUG-level logs for repository layer
    caplog.set_level(logging.DEBUG, logger="app.repositories")

    @log_calls("app.repositories")
    class Sample:
        def foo(self):
            return "foo"

        def _bar(self):
            return "bar"

        @classmethod
        def cls_method(cls):
            return "cls"

        @staticmethod
        def static_method():
            return "static"

    inst = Sample()
    assert inst.foo() == "foo"
    assert inst._bar() == "bar"
    assert inst.cls_method() == "cls"
    assert inst.static_method() == "static"

    recs = [r.getMessage() for r in caplog.records if r.name == "app.repositories"]
    # All four methods should have been wrapped and logged at DEBUG level
    assert "Sample.foo() called." in recs
    assert "Sample._bar() called." in recs
    assert "Sample.cls_method() called." in recs
    assert "Sample.static_method() called." in recs


def test_log_calls_class_method_exception(caplog):
    # capture both INFO entry and ERROR exception
    caplog.set_level(logging.DEBUG, logger="app.repositories")

    @log_calls("app.repositories")
    class Bomb:
        def explode(self):
            raise RuntimeError("kaboom")

    b = Bomb()
    with pytest.raises(RuntimeError):
        b.explode()

    recs = [r.getMessage() for r in caplog.records if r.name == "app.repositories"]
    assert "Bomb.explode() called." in recs
    assert "Bomb.explode() failed with RuntimeError: kaboom" in recs


def test_log_calls_unknown_layer_defaults_to_debug(caplog):
    caplog.set_level(logging.DEBUG, logger="mystery.layer")

    @log_calls("mystery.layer")
    def mystery():
        return "?"

    assert mystery() == "?"

    recs = [r for r in caplog.records if r.name == "mystery.layer"]
    assert len(recs) == 1
    assert recs[0].levelno == logging.DEBUG
    assert recs[0].getMessage() == "mystery() called."
