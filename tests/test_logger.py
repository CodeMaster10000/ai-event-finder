# tests/test_logging_decorator.py

import logging
import pytest
from app.util.logging_util import log_calls, get_log_level

def test_get_log_level():
    assert get_log_level("app.routes") == logging.INFO
    assert get_log_level("my.SERVICE.layer") == logging.INFO
    assert get_log_level("app.repositories") == logging.DEBUG
    assert get_log_level("something.else") == logging.DEBUG

def test_wrap_function_logs_entry(caplog):
    # capture INFO logs for our test‐logger
    caplog.set_level(logging.DEBUG, logger="app.testfunc")

    @log_calls("app.testfunc")
    def foo(a, b=1):
        return a + b

    result = foo(2, b=3)
    assert result == 5

    # we should see exactly one entry log at INFO
    entries = [r for r in caplog.records if r.name == "app.testfunc"]
    assert len(entries) == 1
    assert entries[0].levelno == logging.DEBUG
    assert "foo() called." in entries[0].message

def test_wrap_function_logs_exception(caplog):
    caplog.set_level(logging.INFO, logger="app.testfunc")

    @log_calls("app.testfunc")
    def boom():
        raise ValueError("bad things")

    with pytest.raises(ValueError):
        boom()

    # error path should log the failure message
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert any("boom() failed with ValueError: bad things" in r.message for r in errors)

def test_wrap_class_methods(caplog):
    caplog.set_level(logging.DEBUG, logger="app.testclass")

    @log_calls("app.testclass")
    class Dummy:
        def foo(self, x):
            return x * 2

        def _hidden(self):
            return "no log"

    d = Dummy()
    # public method should log
    val = d.foo(4)
    assert val == 8
    public_logs = [r for r in caplog.records if r.name == "app.testclass"]
    assert any("Dummy.foo() called." in r.message for r in public_logs)

    # private method should not log
    caplog.clear()
    d._hidden()
    assert not caplog.records
