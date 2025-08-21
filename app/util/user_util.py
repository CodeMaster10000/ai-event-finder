"""User Entity Specific Variables"""
NAME_MAX_LENGTH = 50
SURNAME_MAX_LENGTH = 50
EMAIL_MAX_LENGTH = 100
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 256

def return_not_found_by_id_message(id) -> str:
    return f"User not found with id {id}"
def return_not_found_by_name_message(name) -> str:
    return f"User not found with name {name}"
def return_not_found_by_email_message(email) -> str:
    return f"User not found with email {email}"