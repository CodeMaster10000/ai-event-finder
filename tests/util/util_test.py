import os

test_cfg = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"postgresql://{os.getenv('TEST_DB_USER')}:{os.getenv('TEST_DB_PASSWORD')}"
        f"@{os.getenv('TEST_DB_HOST')}:{os.getenv('TEST_DB_PORT')}/{os.getenv('TEST_DB_NAME')}"
    }
