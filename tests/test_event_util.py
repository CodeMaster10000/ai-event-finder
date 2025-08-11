import pytest
from app.util.event_util import (
    return_not_found_by_id_message,
    return_not_found_by_title_message,
    return_not_found_by_category_message,
    return_not_found_by_location_message,
)
from app.constants import (
    TITLE_MAX_LENGTH,
    DESCRIPTION_MAX_LENGTH,
    LOCATION_MAX_LENGTH,
    CATEGORY_MAX_LENGTH,
)

def test_length_constants():
    assert isinstance(TITLE_MAX_LENGTH, int)
    assert isinstance(DESCRIPTION_MAX_LENGTH, int)
    assert isinstance(LOCATION_MAX_LENGTH, int)
    assert isinstance(CATEGORY_MAX_LENGTH, int)

@pytest.mark.parametrize("event_id", [0, 42, 999])
def test_return_not_found_by_id_message(event_id):
    assert return_not_found_by_id_message(event_id) == f"Event not found with id {event_id}"

@pytest.mark.parametrize("title", ["Party", "", "123"])
def test_return_not_found_by_title_message(title):
    assert return_not_found_by_title_message(title) == f"Event not found with title {title}"

@pytest.mark.parametrize("category", ["Music", "Sport", ""])
def test_return_not_found_by_category_message(category):
    expected = f"Event not found with category {category}"
    assert return_not_found_by_category_message(category) == expected

@pytest.mark.parametrize("location", ["Club", "Hall", ""])
def test_return_not_found_by_location_message(location):
    assert return_not_found_by_location_message(location) == f"Event not found with location {location}"
