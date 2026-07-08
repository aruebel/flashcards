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

// --- Karteneditor: Kartentyp (Text / Multiple Choice / Texteingabe / Puzzle) -

let choiceRowCounter = 0;
let puzzleRowCounter = 0;

const CARD_TYPE_HINTS = {
  typed: "Bei der Abfrage muss die Antwort exakt eingetippt werden (Gross-/Kleinschreibung und Leerzeichen zaehlen).",
  puzzle: "Bei der Abfrage bleiben alle Teil-B-Optionen in jeder Zeile auswaehlbar und verschwinden nicht, "
    + "wenn sie schon einer anderen Zeile zugeordnet wurden - das macht die Zuordnung anspruchsvoller.",
};

function onCardTypeChange() {
  const type = document.getElementById("card_type").value;
  const isMultipleChoice = type === "multiple_choice";
  const isPuzzle = type === "puzzle";
  document.getElementById("answer_text_side").classList.toggle("hidden", isMultipleChoice || isPuzzle);
  document.getElementById("choices_side").classList.toggle("hidden", !isMultipleChoice);
  document.getElementById("puzzle_side").classList.toggle("hidden", !isPuzzle);

  const hint = document.getElementById("card_type_hint");
  if (hint) {
    hint.textContent = CARD_TYPE_HINTS[type] || "";
  }
}

function addChoiceRow() {
  const uid = `n${choiceRowCounter++}`;
  const row = document.createElement("div");
  row.className = "choice-row";
  row.dataset.uid = uid;
  row.innerHTML = `
    <input type="checkbox" name="choice_correct_${uid}" value="1">
    <input type="text" name="choice_text_${uid}" placeholder="Antwortoption">
    <button type="button" class="link-button danger" onclick="removeChoiceRow(this)">Entfernen</button>
  `;
  document.getElementById("choice-list").appendChild(row);
  row.querySelector('input[type="text"]').focus();
}

function removeChoiceRow(button) {
  button.closest(".choice-row").remove();
}

function addPuzzleRow() {
  const uid = `n${puzzleRowCounter++}`;
  const row = document.createElement("tr");
  row.className = "puzzle-pair-row";
  row.dataset.uid = uid;
  row.innerHTML = `
    <td><input type="text" name="puzzle_left_${uid}" placeholder="Teil A"></td>
    <td><input type="text" name="puzzle_right_${uid}" placeholder="Teil B"></td>
    <td><button type="button" class="link-button danger" onclick="removePuzzleRow(this)">Entfernen</button></td>
  `;
  document.getElementById("puzzle-pair-list").appendChild(row);
  row.querySelector('input[type="text"]').focus();
}

function removePuzzleRow(button) {
  button.closest(".puzzle-pair-row").remove();
}

// --- Abfrage: Klick auf Bild in voller Groesse anzeigen -------------------

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".quiz-image").forEach((img) => {
    img.addEventListener("click", () => openLightbox(img.src));
  });
});
