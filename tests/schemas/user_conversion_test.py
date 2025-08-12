import pytest
from marshmallow import ValidationError

# 1. Import your schemas
from app.schemas.user_schema import CreateUserSchema, UserSchema

# 2. Import your model/
from app.models.user import User

# 3. A dummy hash function (replace with your real one or mock)
def dummy_hash(raw):
    return f"hashed-{raw}"

@pytest.fixture
def raw_payload():
    return {
        "name": "  Alice  ",
        "surname": "\tSmith\n",
        "email": "  Alice.Smith@Example.COM  ",
        "password": "Secr3tPass"
    }

def test_dto_to_entity_to_dto_roundtrip(raw_payload):
    # 1) LOAD: Validate & normalize incoming data
    loaded = CreateUserSchema().load(raw_payload)

    # 2) MODEL: Instantiate your User entity (hashing password)
    user = User(
        name=loaded["name"],
        surname=loaded["surname"],
        email=loaded["email"],
        password=dummy_hash(loaded["password"])
    )
    # (You could also attach user.id here if you want to test dump_only)

    # 3) DUMP: Serialize back to JSON-safe dict
    dumped = UserSchema().dump(user)

    # 4) ASSERTIONS:
    #   - All leading/trailing whitespace removed
    assert loaded["name"] == "Alice"
    assert loaded["surname"] == "Smith"
    #   - Email is lowercased
    assert loaded["email"] == "alice.smith@example.com"
    #   - Password never shows up in the dumped output
    assert "password" not in dumped
    #   - The fields you expect are present
    assert set(dumped.keys()) == {"name", "surname", "email"}

def test_invalid_password_rejected():
    bad = {
        "name": "Bob",
        "surname": "Jones",
        "email": "bob@example.com",
        "password": "weak"  # too short / missing uppercase or digit
    }
    with pytest.raises(ValidationError):
        CreateUserSchema().load(bad)
