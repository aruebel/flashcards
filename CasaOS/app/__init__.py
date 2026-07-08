"""Flask-Factory fuer das Karteikarten Lernsystem (Web/CasaOS-Variante)."""
import os
import secrets
from pathlib import Path
from typing import Optional

from flask import Flask, g, send_from_directory

from .core.database import Database


def create_app(data_dir: Optional[Path] = None) -> Flask:
    app = Flask(__name__)
    app.config["DATA_DIR"] = Path(data_dir or os.environ.get("DATA_DIR", "./data")).resolve()
    app.config["DATA_DIR"].mkdir(parents=True, exist_ok=True)
    app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB Upload-Limit

    secret_key_path = app.config["DATA_DIR"] / ".secret_key"
    if env_key := os.environ.get("SECRET_KEY"):
        app.secret_key = env_key
    elif secret_key_path.exists():
        app.secret_key = secret_key_path.read_text().strip()
    else:
        key = secrets.token_hex(32)
        secret_key_path.write_text(key)
        app.secret_key = key

    from .routes.topics import topics_bp
    from .routes.cards import cards_bp
    from .routes.quiz import quiz_bp
    from .routes.backup_routes import backup_bp

    app.register_blueprint(topics_bp)
    app.register_blueprint(cards_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(backup_bp)

    @app.get("/media/<path:filename>")
    def media(filename):
        return send_from_directory(app.config["DATA_DIR"] / "images", filename)

    @app.template_filter("media_url")
    def media_url(path):
        return f"/media/{Path(path).name}" if path else None

    static_dir = Path(app.static_folder)

    @app.template_global("asset_version")
    def asset_version(filename: str) -> int:
        """Aenderungszeitpunkt einer statischen Datei, als Cache-Busting-Query-Parameter.

        Ohne das koennten Browser nach einem Deploy weiterhin ein gecachtes
        app.js/style.css verwenden, obwohl der Server bereits neuen Code ausliefert.
        """
        return int((static_dir / filename).stat().st_mtime)

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    return app


def get_db() -> Database:
    from flask import current_app

    if "db" not in g:
        db_path = current_app.config["DATA_DIR"] / "flashcards.db"
        g.db = Database(db_path)
    return g.db
