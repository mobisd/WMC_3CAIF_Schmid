"""Startdatei fuer die Flask-App."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True ist nur fuer lokale Entwicklung gedacht.
    app.run(host="127.0.0.1", port=5000, debug=True)
