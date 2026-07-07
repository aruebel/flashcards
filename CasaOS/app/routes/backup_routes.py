"""Export/Import aller Themen, Karten und Lernfortschritte als .zip-Backup."""
import os
import tempfile
import zipfile
from datetime import date
from pathlib import Path

from flask import (
    Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for,
)

from .. import get_db
from ..core import backup

backup_bp = Blueprint("backup", __name__, url_prefix="/backup")


@backup_bp.get("/export")
def export():
    db = get_db()
    fd, tmp_path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    zip_path = Path(tmp_path)
    zip_path.unlink()  # export_to_zip legt die Datei selbst an
    backup.export_to_zip(db, zip_path)

    filename = f"karteikarten_backup_{date.today().isoformat()}.zip"
    response = send_file(zip_path, as_attachment=True, download_name=filename, mimetype="application/zip")

    @response.call_on_close
    def _cleanup():
        zip_path.unlink(missing_ok=True)

    return response


@backup_bp.get("/import")
def import_form():
    return render_template("backup.html")


@backup_bp.post("/import")
def import_backup():
    db = get_db()
    file = request.files.get("file")
    mode = request.form.get("mode", "merge")

    if file is None or not file.filename:
        flash("Bitte eine .zip-Backup-Datei auswaehlen.", "error")
        return redirect(url_for("backup.import_form"))

    fd, tmp_path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    tmp_zip = Path(tmp_path)
    try:
        file.save(tmp_zip)
        result = backup.import_from_zip(db, current_app.config["DATA_DIR"], tmp_zip, mode=mode)
    except (ValueError, KeyError, OSError, zipfile.BadZipFile) as exc:
        flash(f"Import fehlgeschlagen: {exc}", "error")
        return redirect(url_for("backup.import_form"))
    finally:
        tmp_zip.unlink(missing_ok=True)

    flash(
        f"Import abgeschlossen. Neue Themen: {result.topics_added}, "
        f"neue Karten: {result.cards_added}, uebersprungen: {result.cards_skipped}.",
        "success",
    )
    return redirect(url_for("cards.index"))
