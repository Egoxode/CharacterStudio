import os
import sys
from pathlib import Path

import shiboken6
from PySide6.QtCore import Qt, Signal, QEvent, QSize, QRectF, QTimer
from PySide6.QtGui import (
    QKeySequence, QShortcut, QIcon, QPixmap, QPainter, QPainterPath, QColor, QFont, QPen
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QListView, QPushButton, QTabWidget, QPlainTextEdit, QLabel,
    QFileDialog, QMessageBox, QScrollArea, QFrame
)

from . import __version__
from .card import Card, is_card, new_card_raw
from .library import default_library_dir, import_copy, is_inside, safe_stem, unique_path
from .storage import read_json_file, save_json
from .theme import get_dark_theme

APP_TITLE = "Character Studio by Egoxode"


def plain_text(edit: QPlainTextEdit) -> str:
    """Text of the field exactly as typed. toPlainText() would turn no-break spaces (U+00A0)
    into normal spaces and U+2028 into a line break; the raw text keeps them."""
    return edit.document().toRawText().replace("\u2029", "\n")


def _avatar_icon(size: int = 144, dirty: bool = False) -> QIcon:
    """Placeholder avatar: a silhouette in a circle. Orange dot = unsaved changes."""
    bg, fg = QColor("#0e0e0e"), QColor("#9d88a3")
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    clip = QPainterPath()
    clip.addEllipse(QRectF(0, 0, size, size))
    p.setClipPath(clip)
    p.fillRect(0, 0, size, size, bg)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(fg)
    p.drawEllipse(QRectF(size * 0.18, size * 0.64, size * 0.64, size * 0.62))   # shoulders
    p.setPen(QPen(bg, size * 0.035))
    head = QRectF(size * 0.29, size * 0.13, size * 0.42, size * 0.46)
    p.drawEllipse(head)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(int(size * 0.30))
    p.setFont(font)
    p.setPen(bg)
    p.drawText(head, Qt.AlignmentFlag.AlignCenter, "?")
    p.setClipping(False)
    if dirty:
        p.setPen(QPen(QColor("#1e1e1e"), size * 0.03))
        p.setBrush(QColor("#e8a33d"))
        p.drawEllipse(QRectF(size * 0.74, size * 0.02, size * 0.24, size * 0.24))
    p.end()
    return QIcon(pm)


def _counter_text(text: str) -> str:
    chars = len(text)
    return f"{chars} chars | ~{chars // 4} tokens"


def _parse_tags(text: str, existing: list) -> list:
    """Tags from the input line. If the user did not change the line, keep the original list
    (a tag with a comma inside must not be split in two)."""
    parsed = [x.strip() for x in text.replace("\n", ",").split(",") if x.strip()]
    if [x.strip() for x in ", ".join(existing).split(",") if x.strip()] == parsed:
        return list(existing)
    return parsed


def _field(title: str, widget: QWidget, hint: str, counter: QLabel | None = None) -> QWidget:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 6)
    layout.setSpacing(2)
    head = QHBoxLayout()
    label = QLabel(title)
    label.setObjectName("fieldTitle")
    head.addWidget(label)
    head.addStretch()
    if counter is not None:
        counter.setStyleSheet("color: #888; font-size: 11px;")
        head.addWidget(counter)
    layout.addLayout(head)
    layout.addWidget(widget, 1)
    hint_label = QLabel(hint)
    hint_label.setWordWrap(True)
    hint_label.setStyleSheet("color: #888; font-size: 11px;")
    layout.addWidget(hint_label)
    widget.setToolTip(hint)
    return box


class TagsEdit(QPlainTextEdit):
    """Tags: several lines (wrapped at the field width) instead of one long line. Enter does nothing,
    Tab moves to the next field; text() / setText() / textEdited(str) as in QLineEdit."""
    textEdited = Signal(str)

    def __init__(self, lines=3):
        super().__init__()
        self.setTabChangesFocus(True)
        self.setFixedHeight(self.fontMetrics().lineSpacing() * lines + 14)
        self.textChanged.connect(lambda: self.textEdited.emit(self.text()))

    def text(self) -> str:
        return plain_text(self)

    def setText(self, text: str):
        self.setPlainText(text)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.ignore()
            return
        super().keyPressEvent(event)


def _text_edit(min_height=120) -> QPlainTextEdit:
    edit = QPlainTextEdit()
    edit.setMinimumHeight(min_height)
    return edit


class GreetingBox(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("greetingBox")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        head = QHBoxLayout()
        self.title = QLabel()
        self.btn_up = QPushButton("▲")
        self.btn_down = QPushButton("▼")
        self.btn_delete = QPushButton("Delete")
        for b in (self.btn_up, self.btn_down):
            b.setFixedWidth(36)
        head.addWidget(self.title)
        head.addStretch()
        head.addWidget(self.btn_up)
        head.addWidget(self.btn_down)
        head.addWidget(self.btn_delete)
        layout.addLayout(head)
        self.edit = _text_edit(140)
        self.edit.setPlainText(text)
        layout.addWidget(self.edit)


class GreetingsEditor(QWidget):
    """Alternate greetings: one text box per greeting, add / delete / reorder."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.boxes: list[GreetingBox] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.items = QVBoxLayout()
        self.items.setSpacing(8)
        layout.addLayout(self.items)
        self.empty = QLabel("No alternate greetings.")
        self.empty.setStyleSheet("color: #888;")
        layout.addWidget(self.empty)
        self.btn_add = QPushButton("Add Greeting")
        self.btn_add.clicked.connect(self.add_greeting)
        layout.addWidget(self.btn_add)

    def greetings(self) -> list:
        return [plain_text(b.edit) for b in self.boxes]

    def set_greetings(self, greetings: list):
        for box in self.boxes:
            self.items.removeWidget(box)
            box.deleteLater()
        self.boxes = []
        for text in greetings:
            self._append(text)
        self._update_titles()

    def _append(self, text: str) -> GreetingBox:
        box = GreetingBox(text, self)
        box.edit.textChanged.connect(self._on_text_changed)
        box.btn_up.clicked.connect(lambda: self._move(box, -1))
        box.btn_down.clicked.connect(lambda: self._move(box, 1))
        box.btn_delete.clicked.connect(lambda: self._delete(box))
        self.boxes.append(box)
        self.items.addWidget(box)
        return box

    def _update_titles(self):
        count = len(self.boxes)
        for i, box in enumerate(self.boxes):
            box.title.setText(f"Greeting {i + 1}   ·   {_counter_text(plain_text(box.edit))}")
            box.btn_up.setEnabled(i > 0)
            box.btn_down.setEnabled(i < count - 1)
        self.empty.setVisible(count == 0)

    def _on_text_changed(self):
        self._update_titles()
        self.changed.emit()

    def add_greeting(self):
        box = self._append("")
        self._update_titles()
        box.edit.setFocus()
        self.changed.emit()

    def _move(self, box: GreetingBox, step: int):
        i = self.boxes.index(box)
        j = i + step
        if not 0 <= j < len(self.boxes):
            return
        texts = self.greetings()
        texts[i], texts[j] = texts[j], texts[i]
        self.set_greetings(texts)
        self.boxes[j].edit.setFocus()
        self.changed.emit()

    def _delete(self, box: GreetingBox):
        i = self.boxes.index(box)
        if plain_text(box.edit).strip():
            r = QMessageBox.question(
                self, "Delete Greeting", f"Delete greeting {i + 1}?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if r != QMessageBox.Yes:
                return
        texts = self.greetings()
        del texts[i]
        self.set_greetings(texts)
        self.changed.emit()


class MainWindow(QMainWindow):
    def __init__(self, library_dir=None):
        super().__init__()
        self.library = Path(library_dir) if library_dir else default_library_dir()
        self.export_dir = ""
        self.resize(1500, 900)
        self.setAcceptDrops(True)
        self.icon_clean = _avatar_icon()
        self.icon_dirty = _avatar_icon(dirty=True)
        self.cards: list[Card] = []
        self.current: Card | None = None
        self._loading = False

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)

        # ---- Left: files and card list ----
        left = QVBoxLayout()
        self.btn_new = QPushButton("New Card")
        self.btn_open = QPushButton("Import Files")
        self.btn_folder = QPushButton("Import Folder")
        self.btn_save = QPushButton("Save")
        self.btn_save_all = QPushButton("Save All")
        self.btn_export = QPushButton("Export")
        self.btn_delete = QPushButton("Delete")
        self.btn_new.clicked.connect(self.new_card)
        self.btn_open.clicked.connect(self.import_files)
        self.btn_folder.clicked.connect(self.import_folder)
        self.btn_save.clicked.connect(self.save_current)
        self.btn_save_all.clicked.connect(self.save_all)
        self.btn_export.clicked.connect(self.export_current)
        self.btn_delete.clicked.connect(self.delete_current)
        for b in (self.btn_new, self.btn_open, self.btn_folder, self.btn_save,
                  self.btn_save_all, self.btn_export, self.btn_delete):
            left.addWidget(b)

        self.list = QListWidget()
        self.list.setObjectName("cardGrid")
        self.list.setViewMode(QListView.ViewMode.IconMode)
        self.list.setMovement(QListView.Movement.Static)
        self.list.setResizeMode(QListView.ResizeMode.Adjust)
        self.list.setWrapping(True)
        self.list.setWordWrap(False)
        self.list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.list.setUniformItemSizes(True)
        self.list.setIconSize(QSize(72, 72))
        self.list.setGridSize(QSize(108, 106))
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setMinimumWidth(3 * 108 + 24)
        font = self.list.font()
        font.setBold(True)
        self.list.setFont(font)
        self.list.currentRowChanged.connect(self.on_row_changed)
        left.addWidget(self.list, 1)
        self.drop_hint = QLabel("Drop .json cards or a folder into the window to import them.")
        self.drop_hint.setWordWrap(True)
        self.drop_hint.setStyleSheet("color: #888; font-size: 11px;")
        left.addWidget(self.drop_hint)
        layout.addLayout(left, 0)

        # ---- Right: editor ----
        self.name = QLineEdit()
        self.description = _text_edit(260)
        self.scenario = _text_edit(140)
        self.first_mes = _text_edit(220)
        self.greetings = GreetingsEditor()
        self.mes_example = _text_edit(400)
        self.creator = QLineEdit()
        self.tags = TagsEdit()
        self.creator_notes = _text_edit(220)
        self.personality = _text_edit(160)
        self.system_prompt = _text_edit(160)
        self.post_history_instructions = _text_edit(160)

        self.counters = {k: QLabel() for k in ("description", "scenario", "first_mes", "mes_example", "personality", "system_prompt", "post_history_instructions", "creator_notes")}

        self.tabs = QTabWidget()
        self.tabs.addTab(self._page([
            _field("Name", self.name, "Character name. Used for {{char}}."),
            _field("Description", self.description,
                   "Main character description. Always included in the prompt.", self.counters["description"]),
            _field("Scenario", self.scenario,
                   "Circumstances and context of the interaction.", self.counters["scenario"]),
        ], [0, 2, 1]), "Character")
        self.tabs.addTab(self._page([
            _field("First Message", self.first_mes,
                   "The first message of a new chat.", self.counters["first_mes"]),
            _field("Alternate Greetings", self.greetings,
                   "Other first messages. In SillyTavern they appear as swipes of the first message."),
        ], [1, 0]), "Greetings")
        self.tabs.addTab(self._page([
            _field("Examples of Dialogue", self.mes_example,
                   "Example chat lines. Start each example with <START>.", self.counters["mes_example"]),
        ], [1]), "Examples")
        self.tabs.addTab(self._page([
            _field("Personality", self.personality,
                   "Short summary of the personality. In SillyTavern: Personality summary in Advanced Definitions, "
                   "sent to the AI through {{personality}}.", self.counters["personality"]),
            _field("System Prompt", self.system_prompt,
                   "Main Prompt of this character. In SillyTavern it replaces the main system prompt "
                   "(if Prefer Char. Prompt is on). {{original}} inserts the usual prompt.",
                   self.counters["system_prompt"]),
            _field("Post-History Instructions", self.post_history_instructions,
                   "Sent after the chat history (if Prefer Char. Instructions is on in SillyTavern). "
                   "{{original}} inserts the usual instructions.", self.counters["post_history_instructions"]),
        ], [1, 1, 1]), "Advanced")
        self.tabs.addTab(self._page([
            _field("Created by", self.creator, "Card author."),
            _field("Tags", self.tags, "Tags to embed in the card, separated by commas."),
            _field("Creator's Notes", self.creator_notes,
                   "Notes for users of the card. Not sent to the AI.", self.counters["creator_notes"]),
        ], [0, 0, 1]), "Creator")

        self.info = QLabel()
        self.info.setStyleSheet("color: #888;")
        right = QVBoxLayout()
        right.addWidget(self.tabs, 1)
        right.addWidget(self.info)
        layout.addLayout(right, 3)

        self.name.textChanged.connect(lambda t: self.on_edit("name", t))
        self.creator.textChanged.connect(lambda t: self.on_edit("creator", t))
        self.tags.textEdited.connect(self.on_tags_edit)
        for field in ("description", "scenario", "first_mes", "mes_example", "personality", "system_prompt", "post_history_instructions", "creator_notes"):
            edit = getattr(self, field)
            edit.textChanged.connect(lambda f=field, e=edit: self.on_edit(f, plain_text(e)))
        self.greetings.changed.connect(lambda: self.on_edit("alternate_greetings", self.greetings.greetings()))

        QShortcut(QKeySequence("Ctrl+N"), self, self.new_card)
        QShortcut(QKeySequence("Ctrl+O"), self, self.import_files)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_current)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self.save_all)
        QShortcut(QKeySequence("Ctrl+E"), self, self.export_current)
        # Delete key works only when the card grid has focus, so it never fires while typing.
        delete_key = QShortcut(QKeySequence(QKeySequence.StandardKey.Delete), self.list)
        delete_key.setContext(Qt.ShortcutContext.WidgetShortcut)
        delete_key.activated.connect(self.delete_current)
        # Files dropped anywhere in the window (also on a text field) open as cards
        # instead of being inserted into the text as a path.
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        self.show_card(None)
        self.load_library()

    def _page(self, widgets, stretch) -> QScrollArea:
        """stretch: share of the free space for each field (0 = keep its size).
        Text fields grow with the window and never get smaller than their minimum height."""
        inner = QWidget()
        layout = QVBoxLayout(inner)
        for w, k in zip(widgets, stretch, strict=True):
            layout.addWidget(w, k)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(inner)
        return scroll

    # ---------- List ----------

    def _update_item(self, item: QListWidgetItem, card: Card):
        name = card.values["name"].strip() or "Unnamed"
        item.setText(name)
        item.setIcon(self.icon_dirty if card.dirty else self.icon_clean)
        file = Path(card.path).name if card.path else "not saved"
        tip = f"{name}\n{file} | {card.format}"
        item.setToolTip(tip + ("\nUnsaved changes" if card.dirty else ""))

    def refresh_item(self, card: Card):
        if card in self.cards:
            item = self.list.item(self.cards.index(card))
            if item:
                self._update_item(item, card)

    @staticmethod
    def _sort_key(card: Card):
        name = card.values["name"].strip() or "Unnamed"
        file = Path(card.path).name if card.path else ""
        return name.casefold(), name, file.casefold()

    def _sorted_index(self, card: Card) -> int:
        key = self._sort_key(card)
        others = [c for c in self.cards if c is not card]
        return sum(1 for c in others if self._sort_key(c) <= key)

    def _restore_current_row(self):
        """Inserting or moving items shifts rows; keep the shown card selected without reloading the editor."""
        if self.current in self.cards:
            row = self.cards.index(self.current)
            self.list.setCurrentRow(row)
            self.list.scrollToItem(self.list.item(row))

    def add_card(self, card: Card):
        row = self._sorted_index(card)
        item = QListWidgetItem()
        self._update_item(item, card)
        self.list.blockSignals(True)
        try:
            self.cards.insert(row, card)
            self.list.insertItem(row, item)
            self._restore_current_row()
        finally:
            self.list.blockSignals(False)

    def place_card(self, card: Card):
        """Move the card to its alphabetical position (after a rename or save)."""
        if card not in self.cards:
            return
        old = self.cards.index(card)
        new = self._sorted_index(card)
        if new == old:
            return
        self.list.blockSignals(True)
        try:
            item = self.list.takeItem(old)
            self.cards.pop(old)
            self.cards.insert(new, card)
            self.list.insertItem(new, item)
            self._restore_current_row()
        finally:
            self.list.blockSignals(False)

    def on_row_changed(self, row):
        self.show_card(self.cards[row] if 0 <= row < len(self.cards) else None)

    def select_card(self, card: Card):
        row = self.cards.index(card)
        if self.list.currentRow() == row:
            if self.current is not card:
                self.show_card(card)
        else:
            self.list.setCurrentRow(row)
        self.list.scrollToItem(self.list.item(row))

    # ---------- Editor ----------

    def show_card(self, card: Card | None):
        self.current = card
        self._loading = True
        try:
            v = card.values if card else {}
            self.name.setText(v.get("name", ""))
            self.description.setPlainText(v.get("description", ""))
            self.scenario.setPlainText(v.get("scenario", ""))
            self.first_mes.setPlainText(v.get("first_mes", ""))
            self.greetings.set_greetings(v.get("alternate_greetings", []))
            self.mes_example.setPlainText(v.get("mes_example", ""))
            self.personality.setPlainText(v.get("personality", ""))
            self.system_prompt.setPlainText(v.get("system_prompt", ""))
            self.post_history_instructions.setPlainText(v.get("post_history_instructions", ""))
            self.creator.setText(v.get("creator", ""))
            self.tags.setText(", ".join(v.get("tags", [])))
            self.creator_notes.setPlainText(v.get("creator_notes", ""))
        finally:
            self._loading = False
        self.tabs.setEnabled(card is not None)
        for b in (self.btn_save, self.btn_export, self.btn_delete):
            b.setEnabled(card is not None)
        self.update_counters()
        self.update_status()

    def on_edit(self, field, value):
        if self._loading or self.current is None:
            return
        self.current.set(field, value)
        self.refresh_item(self.current)
        if field == "name":
            self.place_card(self.current)
        self.update_counters()
        self.update_status()

    def on_tags_edit(self, text):
        if self._loading or self.current is None:
            return
        self.on_edit("tags", _parse_tags(text, self.current.saved["tags"]))

    def update_counters(self):
        for field, label in self.counters.items():
            label.setText(_counter_text(plain_text(getattr(self, field))))

    def update_status(self):
        card = self.current
        dirty = any(c.dirty for c in self.cards)
        title = APP_TITLE
        if card:
            title += f" - {card.values['name'].strip() or 'Unnamed'}"
        self.setWindowTitle(title + (" *" if dirty else ""))
        self.btn_save_all.setEnabled(dirty)
        if card is None:
            self.info.setText(f"Version {__version__}. Library: {self.library}. Import a card or create a new one.")
            return
        place = f"cards/{Path(card.path).name}" if card.path else "Not saved yet"
        self.info.setText(f"{card.format}  |  {place}")

    # ---------- Library / import ----------

    def load_library(self):
        """Open every card in the library folder (on start)."""
        try:
            self.library.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(self, "Library", f"Cannot create the library folder:\n{self.library}\n\n{e}")
            return
        skipped, errors = [], []
        for f in sorted(x for x in self.library.glob("*.json") if x.is_file()):
            try:
                raw, style = read_json_file(f)
            except Exception as e:
                errors.append(f"{f.name}: {e}")
                continue
            if not is_card(raw):
                skipped.append(f.name)
                continue
            self.add_card(Card(raw, str(f), style=style))
        if self.cards:
            self.select_card(self.cards[0])
        self._report("Library", skipped, errors)
        self.update_status()

    def _report(self, title, skipped, errors):
        notes = []
        if skipped:
            notes.append("Not character cards (skipped):\n" + "\n".join(skipped))
        if errors:
            notes.append("Could not open:\n" + "\n".join(errors))
        if notes:
            QMessageBox.warning(self, title, "\n\n".join(notes))

    def import_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Import Character Cards", "", "JSON (*.json)")
        if paths:
            self.import_paths(paths)

    def import_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Import Folder")
        if folder:
            self.import_paths([folder])

    def import_paths(self, paths):
        """Copy cards into the library (folders: every .json directly inside). The originals are not touched.
        A card with the same content as an open one is only selected. A file from the library itself
        is not copied: it is selected if open, otherwise opened where it is (as on start)."""
        files = []
        for p in paths:
            p = Path(p)
            if p.is_dir():
                files.extend(sorted(x for x in p.glob("*.json") if x.is_file()))
            elif p.suffix.lower() == ".json":
                files.append(p)

        added, skipped, errors = [], [], []
        first_existing = None
        for f in files:
            # Only files directly in cards/ belong to the library (load_library opens just these).
            in_library = f.resolve().parent == self.library.resolve()
            if in_library:
                existing = next((c for c in self.cards if c.path and Path(c.path).resolve() == f.resolve()), None)
                if existing:
                    first_existing = first_existing or existing
                    continue
            try:
                raw, style = read_json_file(f)
            except Exception as e:
                errors.append(f"{f.name}: {e}")
                continue
            if not is_card(raw):
                skipped.append(f.name)
                continue
            if in_library:
                # Put into cards/ after the start: open it where it is, a copy would be a duplicate.
                card = Card(raw, str(f), style=style)
            else:
                existing = next((c for c in self.cards if c.path and c.raw == raw), None)
                if existing:
                    first_existing = first_existing or existing
                    continue
                try:
                    self.library.mkdir(parents=True, exist_ok=True)
                    target = import_copy(f, self.library, [c.path for c in self.cards if c.path])
                except OSError as e:
                    errors.append(f"{f.name}: {e}")
                    continue
                card = Card(raw, str(target), style=style)
            self.add_card(card)
            added.append(card)

        if added:
            self.select_card(added[0])
        elif first_existing:
            self.select_card(first_existing)
        self._report("Import", skipped, errors)
        if not files:
            QMessageBox.information(self, "Import", "No .json files found.")
        self.update_status()
        return added

    def eventFilter(self, obj, event):
        kind = event.type()
        # Only widgets of this window (not the message boxes).
        if kind in (QEvent.Type.DragEnter, QEvent.Type.DragMove, QEvent.Type.Drop) \
                and isinstance(obj, QWidget) and obj.window() is self:
            mime = event.mimeData()
            paths = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()] if mime and mime.hasUrls() else []
            if paths:
                if kind == QEvent.Type.Drop:
                    # Open after the drop has finished: a message box inside the drop handler
                    # would block the file manager that started the drag (Windows).
                    QTimer.singleShot(0, lambda: self.import_paths(paths))
                # Always "copied": with Shift the system proposes "move", and after that answer
                # Windows Explorer may delete the original file. The program only reads it.
                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
                return True
        return super().eventFilter(obj, event)

    # ---------- New / Delete ----------

    def new_card(self):
        card = Card(new_card_raw(), None, is_new=True)
        self.add_card(card)
        self.select_card(card)
        self.tabs.setCurrentIndex(0)
        self.name.setFocus()
        self.name.selectAll()

    def delete_current(self):
        card = self.current
        if card is None:
            return
        name = card.values["name"].strip() or "Unnamed"
        where = f"\n\nThe file cards/{Path(card.path).name} will be deleted." if card.path else ""
        r = QMessageBox.question(
            self, "Delete Card",
            f"Delete \"{name}\" from the library?{where}\nFiles you imported it from are not affected.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if r != QMessageBox.Yes:
            return
        if card.path:
            try:
                os.remove(card.path)
            except FileNotFoundError:
                pass
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Failed to delete file:\n{e}")
                return
        row = self.cards.index(card)
        # Qt changes the current row while an item is removed, and the signal it sends
        # (if any) refers to the list before removal. Remove silently, then pick the next card ourselves.
        self.list.blockSignals(True)
        try:
            self.cards.pop(row)
            self.list.takeItem(row)
            row = min(row, len(self.cards) - 1)
            self.list.setCurrentRow(row)
        finally:
            self.list.blockSignals(False)
        self.show_card(self.cards[row] if row >= 0 else None)

    # ---------- Save / Export ----------

    def save_current(self):
        if self.current:
            self.save_card(self.current)

    def save_all(self):
        for card in list(self.cards):
            if card.dirty:
                self.select_card(card)
                if not self.save_card(card):
                    return False
        return True

    def _check_name(self, card: Card, action: str) -> bool:
        if card.values["name"].strip():
            return True
        QMessageBox.warning(self, action, "The card needs a name.")
        self.select_card(card)
        self.tabs.setCurrentIndex(0)
        self.name.setFocus()
        return False

    def save_card(self, card: Card) -> bool:
        """Save into the library. A new card gets a file named after the character."""
        if not self._check_name(card, "Save"):
            return False
        if not card.dirty:
            return True
        path = card.path
        try:
            if not path:
                self.library.mkdir(parents=True, exist_ok=True)
                taken = [c.path for c in self.cards if c.path]
                path = str(unique_path(self.library, safe_stem(card.values["name"]), taken))
            data = card.to_json()
            save_json(path, data, card.style)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")
            return False
        card.mark_saved(data, path)
        self.refresh_item(card)
        self.place_card(card)
        self.update_status()
        return True

    def export_current(self):
        """Write a copy of the card (as shown, including unsaved edits) anywhere outside the library."""
        card = self.current
        if card is None or not self._check_name(card, "Export"):
            return False
        start = str(Path(self.export_dir or Path.home()) / (safe_stem(card.values["name"]) + ".json"))
        path, _ = QFileDialog.getSaveFileName(self, "Export Character Card", start, "JSON (*.json)")
        if not path:
            return False
        if Path(path).suffix.lower() != ".json":  # "my.card" -> "my.card.json"
            path += ".json"
        if is_inside(path, self.library):
            QMessageBox.warning(self, "Export", "Choose a folder outside the library (cards/).")
            return False
        try:
            save_json(path, card.to_json(), card.style)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export file:\n{e}")
            return False
        self.export_dir = str(Path(path).parent)
        return True

    def closeEvent(self, event):
        dirty = [c for c in self.cards if c.dirty]
        if not dirty:
            event.accept()
            return
        names = "\n".join(c.values["name"].strip() or "Unnamed" for c in dirty)
        r = QMessageBox.question(
            self, "Unsaved Changes", f"Save changes before closing?\n\n{names}",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes
        )
        if r == QMessageBox.Cancel:
            event.ignore()
        elif r == QMessageBox.Yes:
            event.accept() if self.save_all() else event.ignore()
        else:
            event.accept()


def run():
    app = QApplication(sys.argv)
    app.setStyleSheet(get_dark_theme())
    w = MainWindow()
    w.show()
    code = app.exec()
    # Сигналы держат окно через лямбды, поэтому само оно не удаляется. Удаляем его явно,
    # пока QApplication ещё жив, иначе при выходе бывает Segmentation fault.
    shiboken6.delete(w)
    sys.exit(code)
