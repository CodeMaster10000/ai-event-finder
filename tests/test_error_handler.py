# tests/test_error_handlers.py
import pytest
from flask import Flask
from app.error_handler.exceptions import (
    UserNotFoundException,
    DuplicateEmailException,
    UserSaveException,
    UserDeleteException,
)
from app.error_handler.global_error_handler import register_error_handlers

@pytest.fixture
def app():
    app = Flask(__name__)
    register_error_handlers(app)

    @app.route("/notfound/<int:id>")
    def not_found(id):
        raise UserNotFoundException(user_id=id)

    @app.route("/duplicate-email")
    def duplicate_email():
        raise DuplicateEmailException("foo@bar.com")

    @app.route("/save-error")
    def save_error():
        # simulate an underlying DB error
        raise UserSaveException(Exception("DB write failed"))

    @app.route("/delete-error")
    def delete_error():
        raise UserDeleteException(user_id=99, original_exception=Exception("DB delete failed"))

    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_user_not_found_handler(client):
    resp = client.get("/notfound/42")
    assert resp.status_code == 404
    assert resp.get_json() == {
        "error": {
            "code": "USER_NOT_FOUND",
            "message": "User with id=42 not found."
        }
    }

def test_duplicate_email_handler(client):
    resp = client.get("/duplicate-email")
    assert resp.status_code == 409
    assert resp.get_json() == {
        "error": {
            "code": "DUPLICATE_EMAIL",
            "message": "User with email foo@bar.com already exists."
        }
    }

def test_user_save_exception_handler(client):
    resp = client.get("/save-error")
    assert resp.status_code == 500
    payload = resp.get_json()["error"]
    assert payload["code"] == "USER_SAVE_ERROR"
    assert "Unable to save user due to an internal error." in payload["message"]

def test_user_delete_exception_handler(client):
    resp = client.get("/delete-error")
    assert resp.status_code == 500
    payload = resp.get_json()["error"]
    assert payload["code"] == "USER_DELETE_ERROR"
    assert "Unable to delete user with id=99." in payload["message"]
