from __future__ import annotations

import logging
import os
import sys

import database
from flask import Flask, jsonify
from routes.decisions import decisions_bp


def _configure_logging(debug: bool) -> None:
    """
    Structured log output.
    In production you would ship these to a log aggregator.
    Keeping it simple here: one line per record, easy to grep.
    """
    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s %(levelname)-8s %(name)s  %(message)s"
    logging.basicConfig(stream=sys.stdout, level=level, format=fmt, force=True)


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)

    # Defaults
    app.config.setdefault("DB_PATH", "decisions.db")
    app.config.setdefault("DEBUG", False)
    app.config.setdefault("TESTING", False)

    # Caller-supplied overrides (used in tests to get an in-memory DB)
    if config:
        app.config.update(config)

    # Logging
    _configure_logging(app.config["DEBUG"])

    # Database
    database.configure(app.config["DB_PATH"])
    database.init_db()

    # CORS - allow frontend to talk to backend
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
        return response

    @app.route("/api/<path:path>", methods=["OPTIONS"])
    def handle_options(path):
        return "", 204

    # Health check
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    # Routes
    app.register_blueprint(decisions_bp)

    app.logger.info("App created (DB: %s)", app.config["DB_PATH"])
    return app