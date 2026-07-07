"""Themen verwalten: anlegen, umbenennen, loeschen."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import get_db

topics_bp = Blueprint("topics", __name__, url_prefix="/topics")


@topics_bp.get("/")
def list_topics():
    db = get_db()
    return render_template("topics.html", topics=db.list_topics())


@topics_bp.post("/new")
def add_topic():
    db = get_db()
    name = request.form.get("name", "")
    try:
        db.add_topic(name)
        flash(f"Thema '{name.strip()}' angelegt.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("topics.list_topics"))


@topics_bp.post("/<int:topic_id>/rename")
def rename_topic(topic_id):
    db = get_db()
    new_name = request.form.get("name", "")
    try:
        db.rename_topic(topic_id, new_name)
        flash("Thema umbenannt.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("topics.list_topics"))


@topics_bp.post("/<int:topic_id>/delete")
def delete_topic(topic_id):
    db = get_db()
    db.delete_topic(topic_id)
    flash("Thema und zugehoerige Karten geloescht.", "success")
    return redirect(url_for("topics.list_topics"))
