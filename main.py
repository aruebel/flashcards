"""Einstiegspunkt fuer das Karteikarten Lernsystem."""
from pathlib import Path

from flashcards.database import Database
from flashcards.gui.app import FlashcardApp

BASE_DIR = Path(__file__).parent / "data"
DB_PATH = BASE_DIR / "flashcards.db"


def main():
    db = Database(DB_PATH)
    app = FlashcardApp(db, BASE_DIR)
    try:
        app.mainloop()
    finally:
        db.close()


if __name__ == "__main__":
    main()
