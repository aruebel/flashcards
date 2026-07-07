// --- Dark-Mode-Toggle --------------------------------------------------------

function toggleTheme() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const next = isDark ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
  updateThemeButton();
}

function updateThemeButton() {
  const btn = document.getElementById('theme-toggle');
  if (!btn) return;
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  btn.textContent = isDark ? '☀' : '🌙';
  btn.title = isDark ? 'Heller Modus' : 'Dunkler Modus';
}

document.addEventListener('DOMContentLoaded', updateThemeButton);

// Gemeinsame Hilfsfunktionen: Vollbild-Lightbox fuer Bilder + Bild-Upload
// (Datei-Auswahl oder Clipboard-Paste) fuer den Karteneditor.

function openLightbox(url) {
  if (!url) return;
  const lightbox = document.getElementById("lightbox");
  const img = document.getElementById("lightbox-img");
  img.src = url;
  lightbox.classList.remove("hidden");
}

function closeLightbox() {
  document.getElementById("lightbox").classList.add("hidden");
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeLightbox();
});

// --- Karteneditor: Bild je Seite (Frage/Antwort) -------------------------

let activeImageSide = "question";

function setActiveSide(side) {
  activeImageSide = side;
}

async function uploadImageBlob(blob, side) {
  const formData = new FormData();
  formData.append("file", blob, blob.name || "pasted.png");

  const response = await fetch("/cards/image-upload", { method: "POST", body: formData });
  const data = await response.json();
  if (!response.ok) {
    alert(data.error || "Bild-Upload fehlgeschlagen.");
    return;
  }
  setSideImage(side, data.path, data.url);
}

function setSideImage(side, path, url) {
  document.getElementById(`${side}_image_path`).value = path;
  const preview = document.getElementById(`${side}_preview`);
  preview.src = url;
  preview.classList.remove("hidden");
  document.getElementById(`${side}_placeholder`).classList.add("hidden");
}

function removeSideImage(side) {
  document.getElementById(`${side}_image_path`).value = "";
  const preview = document.getElementById(`${side}_preview`);
  preview.src = "";
  preview.classList.add("hidden");
  document.getElementById(`${side}_placeholder`).classList.remove("hidden");
}

function initImageSide(side) {
  const textarea = document.getElementById(`${side}_text`);
  if (textarea) {
    textarea.addEventListener("focus", () => setActiveSide(side));
  }
  const fileInput = document.getElementById(`${side}_image_file`);
  if (fileInput) {
    fileInput.addEventListener("change", () => {
      if (fileInput.files.length > 0) {
        uploadImageBlob(fileInput.files[0], side);
        fileInput.value = "";
      }
    });
  }
  const preview = document.getElementById(`${side}_preview`);
  if (preview) {
    preview.addEventListener("click", () => openLightbox(preview.src));
  }
}

document.addEventListener("paste", (event) => {
  const items = event.clipboardData ? event.clipboardData.items : [];
  for (const item of items) {
    if (item.type.startsWith("image/")) {
      const blob = item.getAsFile();
      uploadImageBlob(blob, activeImageSide);
      event.preventDefault();
      break;
    }
  }
});

// --- Abfrage: Klick auf Bild in voller Groesse anzeigen -------------------

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".quiz-image").forEach((img) => {
    img.addEventListener("click", () => openLightbox(img.src));
  });
});
