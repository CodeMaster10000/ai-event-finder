import pytest
import logging
from flask import Flask
from app.configuration.logging_config import configure_logging, log_calls


def test_configure_logging_levels_and_handlers():
    # Create a Flask app and configure logging
    app = Flask(__name__)
    configure_logging(app)

    # Root logger should be DEBUG and have exactly one StreamHandler
    assert app.logger.level == logging.DEBUG
    handlers = [h for h in app.logger.handlers if isinstance(h, logging.StreamHandler)]
    assert len(handlers) == 1
    console_h = handlers[0]
    assert console_h.level == logging.DEBUG
    fmt = console_h.formatter._fmt
    assert "%(__asctime__)s %(levelname)-5s %(name)s: %(message)s".replace("__asctime__", "asctime") in fmt

    # Child loggers for each layer
    assert app.logger.getChild("routes").level == logging.INFO
    assert app.logger.getChild("services").level == logging.INFO
    assert app.logger.getChild("repositories").level == logging.DEBUG

    # Werkzeug should be quieted to WARNING
    assert logging.getLogger("werkzeug").level == logging.WARNING


def test_log_calls_function_entry_exit(caplog):
    @log_calls("routes.user_route")
    def add(a, b, c=0):
        return a + b + c

    caplog.set_level(logging.INFO, logger="app.routes.user_route")
    result = add(1, 2, c=3)
    assert result == 6

    # Should log entry at INFO level with qualified function name
    msgs = [r.message for r in caplog.records]
    assert any(
        add.__qualname__ in m and "Enter" in m and "args=(1, 2)" in m and "'c': 3" in m
        for m in msgs
    )


def test_log_calls_exception_logs_and_raises(caplog):
    @log_calls("services.user_service_impl")
    def fail():
        raise RuntimeError("fail")

    caplog.set_level(logging.INFO, logger="app.services.user_service_impl")
    with pytest.raises(RuntimeError):
        fail()

    records = caplog.records
    # First record should be INFO, second ERROR
    assert records[0].levelno == logging.INFO
    assert records[1].levelno == logging.ERROR
    # Exception log should include qualified function name
    assert any(
        f"Exception in {fail.__qualname__}" in r.message
        for r in records
    )


def test_log_calls_wraps_class_methods(caplog):
    @log_calls("repositories.user_repository_impl")
    class DummyRepo:
        def process(self, x):
            return x * 2

        def _private(self):
            return 'no log'

    repo = DummyRepo()
    caplog.set_level(logging.DEBUG, logger="app.repositories.user_repository_impl")

    # Public method should be wrapped and logged
    result = repo.process(7)
    assert result == 14

    msgs = [r.message for r in caplog.records]
    method_name = f"{DummyRepo.__qualname__}.process"
    # Enter log for class method at DEBUG level
    assert any(
        method_name in m and "Enter" in m and "args=(" in m and ", 7" in m
        for m in msgs
    )

    # Private method should not be logged
    caplog.clear()
    assert repo._private() == 'no log'
    assert caplog.records == []
