from marshmallow import Schema, fields, validate, EXCLUDE, pre_load
from app.schemas.user_schema import UserSchema
from app.util.event_util import (
    TITLE_MAX_LENGTH, CATEGORY_MAX_LENGTH, LOCATION_MAX_LENGTH, DESCRIPTION_MAX_LENGTH)


class CreateEventSchema(Schema):
    """
    Schema for incoming event creation payload.
    Validates and deserializes client-provided data.
    Pre-processes string fields: trims whitespace.
    Enforces string length and date format.
    """
    class Meta:
        # Drop any unknown fields instead of raising errors
        unknown = EXCLUDE

    @pre_load
    def strip_strings(self, data, **kwargs):
        """
        Trim leading/trailing whitespace on 'name' and 'surname'.
        """
        for key in ("title", "description", "location", "category"):
            val = data.get(key)
            if isinstance(val, str):
                data[key] = val.strip()
        return data


    """
    Title field:
      - Required
      - Must be between 1 and 50 characters after trimming
    """
    title = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=TITLE_MAX_LENGTH),
        error_messages={
            "required": "Title is required.",
            "invalid": f"Title must be a string between 1 and {TITLE_MAX_LENGTH} characters."
        }
    )

    """
    Description field:
      - Required
      - Must be between 1 and 500 characters after trimming
    """
    description = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=DESCRIPTION_MAX_LENGTH),
        error_messages={
            "required": "Description is not required.",
            "invalid": f"Description must be a string between 0 and {DESCRIPTION_MAX_LENGTH} characters."
        }
    )

    """
    Location field:
      - Required
      - Must be between 1 and 50 characters after trimming
    """
    location = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=LOCATION_MAX_LENGTH),
        error_messages={
            "required": "Location is required.",
            "invalid": f"Location must be a string between 0 and {LOCATION_MAX_LENGTH} characters."
        }
    )

    """
    Category field:
      - Required
      - Must be between 1 and 50 characters after trimming
    """
    category = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=CATEGORY_MAX_LENGTH),
        error_messages={
            "required": "Category is required.",
            "invalid": f"Category must be a string between 0 and {CATEGORY_MAX_LENGTH} characters."
        }
    )

    """
    Datetime field:
        - Required
        - Must be a valid date and time format
    """
    datetime = fields.DateTime(
        required=True,
        format="%Y-%m-%d %H:%M:%S",  # The default format, it can be adjusted
        error_messages={
            "required": "Date and time are required.",
            "invalid": "Must be a valid datetime in 'YYYY-MM-DD HH:MM:SS' format."
        }
    )

    organizer_email = fields.Email(
        required=True,
        error_messages={"required": "Organizer email is required."}
    )


class EventSchema(Schema):
    """
    Schema for outgoing event data.
    Serializes internal user model into safe JSON.
    """
    class Meta:
        # Exclude any unexpected attributes when dumping
        unknown = EXCLUDE
        # Preserve field declaration order in output
        ordered = True

    title = fields.Str(
        dump_only=True,
        metadata={"description": "The event title"}
    )
    description = fields.Str(
        dump_only=True,
        metadata={"description":"The event description"}
    )
    # fix to show in a better format
    datetime = fields.Str(
        dump_only=True,
        metadata={"description":"The event host date and time"}
    )
    location = fields.Str(
        dump_only=True,
        metadata={"description": "The location where the event is hosted"}
    )
    category = fields.Str(
        dump_only=True,
        metadata={"description": "The event category"}
    )
    guests = fields.List(
        fields.Nested(UserSchema(only=("name", "surname"))),
        dump_only=True,
        metadata={"description": "List of users attending the event"}
    )
    organizer = fields.Nested(
        UserSchema(only=("name", "surname", "email")),
        dump_only=True,
        metadata={"description": "The event organizer information"}
    )


