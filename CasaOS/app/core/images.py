"""Speichern von hochgeladenen/eingefuegten Bildern im lokalen images-Ordner.

Anders als die Desktop-Variante (die per PIL.ImageGrab direkt auf die
Windows-Zwischenablage zugreift) bekommt die Web-Variante Bild-Bytes vom
Browser geliefert: entweder ueber ein normales <input type="file"> oder per
JavaScript aus einem Clipboard-Paste-Event, das die Bytes per fetch() an
/media/upload schickt. Beides landet hier als reine Bytes.
"""
import uuid
from pathlib import Path
from typing import Optional


def images_dir(base_dir: Path) -> Path:
    path = base_dir / "images"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_image_bytes(data: bytes, suffix: str, base_dir: Path) -> str:
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    filename = f"{uuid.uuid4().hex}{suffix or '.png'}"
    dest = images_dir(base_dir) / filename
    dest.write_bytes(data)
    return str(dest)


def delete_image(path: Optional[str]):
    if path and Path(path).exists():
        Path(path).unlink()
