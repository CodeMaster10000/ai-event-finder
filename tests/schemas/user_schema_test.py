# tests/user_schema_test.py
import pytest
from marshmallow import ValidationError

from app.schemas.user_schema import (
    CreateUserSchema,
    UserSchema,
)

@pytest.fixture
def valid_payload():
    return {
        "name": "  Alice  ",
        "surname": "  Smith ",
        "email": "  Alice.Smith@Example.COM  ",
        "password": "Secr3tPass"
    }

def test_create_user_schema_loads_and_normalizes(valid_payload):
    data = CreateUserSchema().load(valid_payload)
    # leading/trailing whitespace stripped
    assert data["name"] == "Alice"
    assert data["surname"] == "Smith"
    # email trimmed and lowercased
    assert data["email"] == "alice.smith@example.com"
    # password stays as given (to be hashed later)
    assert data["password"] == valid_payload["password"]

def test_create_user_schema_rejects_short_password(valid_payload):
    payload = dict(valid_payload, password="Short1")
    with pytest.raises(ValidationError) as ei:
        CreateUserSchema().load(payload)
    # should mention minimum length
    assert "Password must be at least" in str(ei.value)

def test_create_user_schema_rejects_password_without_upper_or_digit(valid_payload):
    for bad in ["alllowercase1", "ALLUPPERCASE", "NoDigitsHere"]:
        payload = dict(valid_payload, password=bad)
        with pytest.raises(ValidationError):
            CreateUserSchema().load(payload)

def test_create_user_schema_rejects_extra_fields(valid_payload):
    payload = dict(valid_payload, foo="bar")
    data = CreateUserSchema().load(payload)
    # unknown fields are dropped
    assert "foo" not in data

def test_user_schema_dumps_only_public_fields():
    # simulate a User-like object or dict
    user_obj = {
        "id": 123,
        "name": "Bob",
        "surname": "Jones",
        "email": "bob@example.com",
        "password": "secret",            # shouldn't appear
        "created_at": "bogus",           # dropped by unknown=EXCLUDE
    }
    dumped = UserSchema().dump(user_obj)
    assert dumped == {
        "id": 123,
        "name": "Bob",
        "surname": "Jones",
        "email": "bob@example.com",
    }

@pytest.mark.parametrize("field", ["name","surname","email","password"])
def test_create_user_schema_requires_fields(valid_payload, field):
    payload = dict(valid_payload)
    del payload[field]
    with pytest.raises(ValidationError) as exc:
        CreateUserSchema().load(payload)
    assert field in exc.value.messages

@pytest.mark.parametrize("field", ["name","surname"])
def test_rejects_blank_only_strings(valid_payload, field):
    bad = dict(valid_payload, **{field: "   "})
    with pytest.raises(ValidationError) as exc:
        CreateUserSchema().load(bad)
    assert field in exc.value.messages

def test_invalid_email_format(valid_payload):
    bad = dict(valid_payload, email="not-an-email")
    with pytest.raises(ValidationError) as exc:
        CreateUserSchema().load(bad)
    assert "email" in exc.value.messages

