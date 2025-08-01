"""
Centralized logging configuration using dictConfig,
plus decorator to auto-log method/function calls.
"""
import logging
import logging.config

LOGGING = {
  "version": 1,
  "disable_existing_loggers": False,   # ← critical!
  "formatters": {
    "default": { "format": "%(asctime)s %(levelname)-5s %(name)s: %(message)s" }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "formatter": "default",
      "level": "DEBUG"
    }
  },
  "loggers": {
    "app": {
      "level": "DEBUG",
      "propagate": True
    },
    "app.routes": {
      "level": "NOTSET",
      "propagate": True    # so after handling, it passes to "app"
    },
    "app.services":{
        "level": "NOTSET",
        "propagate": True
    },
    "app.repositories":{
        "level": "NOTSET",
        "propagate": True
    },
    "werkzeug":{
        "level":"ERROR"
    }
  },
  "root": {
    "level": "WARNING",
    "handlers": ["console"]
  }
}

def configure_logging():
    # Set Werkzeug logger to ERROR level
    # Create console handler
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    fmt = '%(asctime)s %(levelname)-5s %(name)s: %(message)s'
    console.setFormatter(logging.Formatter(fmt, datefmt='%H:%M:%S'))
    logging.config.dictConfig(LOGGING)




