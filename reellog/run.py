"""Entry point. Run with `flask --app run run` or `python run.py`."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True is for local development only (see README prod notes).
    app.run(host="127.0.0.1", port=5000, debug=True)
