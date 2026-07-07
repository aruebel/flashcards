"""Speichern von eingefuegten Bildern/Screenshots im lokalen images-Ordner."""
import shutil
import uuid
from pathlib import Path
from typing import Optional

from PIL import Image, ImageGrab


def images_dir(base_dir: Path) -> Path:
    path = base_dir / "images"
    path.mkdir(parents=True, exist_ok=True)
    return path


def grab_clipboard_image() -> Optional[Image.Image]:
    img = ImageGrab.grabclipboard()
    if isinstance(img, Image.Image):
        return img
    return None


def save_image(image: Image.Image, base_dir: Path) -> str:
    filename = f"{uuid.uuid4().hex}.png"
    dest = images_dir(base_dir) / filename
    image.save(dest, format="PNG")
    return str(dest)


def import_image_file(source_path: str, base_dir: Path) -> str:
    suffix = Path(source_path).suffix or ".png"
    filename = f"{uuid.uuid4().hex}{suffix}"
    dest = images_dir(base_dir) / filename
    shutil.copy(source_path, dest)
    return str(dest)


def delete_image(path: Optional[str]):
    if path and Path(path).exists():
        Path(path).unlink()
