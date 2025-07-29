from app import create_app, db
from sqlalchemy import text  # ✅ Import this at the top

app = create_app()

@app.route("/test-db")
def test_db():
    try:
        db.session.execute(text("SELECT 1"))  # ✅ Wrap with text()
        return "✅ Database connected successfully!"
    except Exception as e:
        return f"❌ Database connection failed: {e}"


if __name__ == "__main__":
    app.run()
