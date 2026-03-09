"""Entry point for the development server."""
from app import create_app

app = create_app({"DEBUG": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
