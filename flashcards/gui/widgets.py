"""Wiederverwendbare GUI-Hilfsfunktionen und -Widgets."""
import tkinter as tk
from pathlib import Path
from typing import Optional

from PIL import Image, ImageTk

MAX_IMAGE_WIDTH = 480
MAX_IMAGE_HEIGHT = 320
FULL_VIEW_SCREEN_FRACTION = 0.9


def load_scaled_photo(path: str, max_w: int = MAX_IMAGE_WIDTH, max_h: int = MAX_IMAGE_HEIGHT) -> Optional[ImageTk.PhotoImage]:
    if not path or not Path(path).exists():
        return None
    img = Image.open(path)
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return ImageTk.PhotoImage(img)


def show_full_image(master, path: str):
    """Oeffnet das Bild in voller (bzw. bildschirmfuellender) Groesse in einem eigenen Fenster."""
    if not path or not Path(path).exists():
        return

    top = tk.Toplevel(master)
    top.title("Bild - volle Groesse")
    top.configure(bg="#000000")

    max_w = int(top.winfo_screenwidth() * FULL_VIEW_SCREEN_FRACTION)
    max_h = int(top.winfo_screenheight() * FULL_VIEW_SCREEN_FRACTION)
    img = Image.open(path)
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    photo = ImageTk.PhotoImage(img)

    label = tk.Label(top, image=photo, bg="#000000", cursor="hand2")
    label.image = photo
    label.pack()

    top.bind("<Escape>", lambda _e: top.destroy())
    label.bind("<Button-1>", lambda _e: top.destroy())
    top.focus_set()


class ImagePanel(tk.Frame):
    """Zeigt ein Bild an und haelt eine Referenz darauf (verhindert GC).

    Ist ein Frame (statt Label), weil bei Label -width/-height ohne Bild in
    Zeichen/Zeilen statt Pixeln interpretiert werden - width=200, height=120
    ergab dadurch eine riesige Platzhalterflaeche statt 200x120 Pixel. Als
    Frame sind width/height immer Pixelwerte, per pack_propagate(False) bleibt
    die reservierte Groesse auch ohne Bild stabil.

    Ein Klick auf das angezeigte (evtl. verkleinerte) Bild oeffnet es in
    voller Groesse in einem eigenen Fenster.
    """

    def __init__(self, master, width: int = 0, height: int = 0, bg: Optional[str] = None, **kwargs):
        super().__init__(master, width=width, height=height, bg=bg, **kwargs)
        if width or height:
            self.pack_propagate(False)
        self._label = tk.Label(self, bg=bg)
        self._label.pack(fill=tk.BOTH, expand=True)
        self._label.bind("<Button-1>", self._on_click)
        self._photo = None
        self._image_path = None

    def set_image_path(self, path: Optional[str]):
        photo = load_scaled_photo(path) if path else None
        self._photo = photo
        self._image_path = path if photo else None
        self._label.configure(image=photo if photo else "", text="" if photo else "")
        self._label.configure(cursor="hand2" if photo else "")

    def clear(self):
        self._photo = None
        self._image_path = None
        self._label.configure(image="", text="", cursor="")

    def _on_click(self, _event):
        if self._image_path:
            show_full_image(self, self._image_path)
