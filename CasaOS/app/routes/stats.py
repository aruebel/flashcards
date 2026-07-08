"""Statistik-Uebersicht: Lernfortschritt je Thema in Prozent."""
from flask import Blueprint, render_template

from .. import get_db

stats_bp = Blueprint("stats", __name__)


@stats_bp.get("/statistik")
def overview():
    db = get_db()
    return render_template("stats.html", topic_stats=db.topic_stats())
