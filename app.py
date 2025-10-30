"""Main application entry point."""

from src.web import create_app
from src.config import get_config

if __name__ == "__main__":
    config = get_config()
    app = create_app()
    app.run(
        host="0.0.0.0",
        port=config.flask_port,
        debug=config.flask_debug
    )

