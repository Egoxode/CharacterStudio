# Character Studio

Desktop editor for SillyTavern character cards in JSON format.

Version **1.0.7** ([changelog](CHANGELOG.md))

Character Studio edits only the card fields you use most. Everything else in the file is kept exactly as it was. You can freely use, copy, and modify this program.

## AI Disclaimer

This project was edited with an AI assistant. Read the code before you rely on it.

## Features

- Edit: Name, Description, Scenario, First Message, Alternate Greetings, Examples of Dialogue, Personality, System Prompt, Post-History Instructions (Advanced tab), Created by, Tags, Creator's Notes
- Alternate greetings: add, delete (with confirmation), and reorder
- Own card library (`cards/` folder next to the program), opened automatically on start
- Import files, a whole folder, or drag `.json` files / a folder anywhere into the window. The originals are copied and never changed
- Cards are shown as a grid of avatars, like in SillyTavern, always sorted by name (A–Z, case-insensitive). Hover a card to see its file and format
- An orange dot on the avatar marks unsaved changes; edits are kept when you switch between cards
- Character and token estimates for long fields
- New card in Character Card V2 format (the format SillyTavern uses)
- Export a copy of a card anywhere, for example to load it into SillyTavern
- Dark theme

## Requirements

- Windows, Linux, or macOS
- Python 3.10 or newer
- `pip`

## Install

### 1. Install Python

Install Python 3.10+ from [python.org](https://www.python.org/downloads/).

During setup on Windows, enable:

- **Add python.exe to PATH**

Check that Python works:

```bash
python --version
```

If `python` is not found, try:

```bash
py --version
```

### 2. Download the program

Clone the repository:

```bash
git clone https://github.com/Egoxode/CharacterStudio.git
cd CharacterStudio
```

Or download the ZIP from GitHub and unpack it, then open that folder in a terminal.

### 3. Create a virtual environment (recommended)

**Windows:**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

After activation, your terminal prompt should show `(.venv)`.

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

This installs `PySide6` (interface).

### 5. Run

```bash
python main.py
```

On some systems:

```bash
python3 main.py
```

or:

```bash
py main.py
```

### Run without a console window (Windows)

Double-click `CharacterStudio.pyw`. The program opens without the black console window. If something goes wrong, the error is shown in a message box and written to `error.log` next to the program. The same happens when you start the program with `python main.py` (or double-click `main.py`): errors are written to `error.log` and shown in a message box, and also printed in the console.

## Keyboard shortcuts

- `Ctrl+N` — New card
- `Ctrl+O` — Import files
- `Ctrl+S` — Save current card
- `Ctrl+Shift+S` — Save all changed cards
- `Ctrl+E` — Export current card
- `Delete` (card grid focused) — Delete card from the library

## Troubleshooting

**`python` is not recognized**  
Python is not in PATH. Reinstall Python and enable **Add python.exe to PATH**, or use `py` instead of `python`.

**`No module named PySide6`**  
Dependencies were not installed, or you are not inside the virtual environment. Run `pip install -r requirements.txt` again.

**`No module named app`**  
Run `python main.py` from the project root folder, the same folder that contains `main.py` and `app/`.

**A file is listed as "Not character cards (skipped)"**  
The JSON is not a character card (for example, a lorebook) or it is a card format the program does not recognize.

## Usage notes

### Library

Character Studio keeps its own copies of your cards in the `cards/` folder next to `main.py`. All cards from this folder are opened when the program starts.

- **Import Files** (`Ctrl+O`), **Import Folder**, or drag and drop copy cards into the library. After that the program works only with the copy; the original file is never changed.
- Importing a card that is already in the library (same content) just selects it. If the content is different, it is added as a new card with a number, for example `Alcina_Dimitrescu (2).json`.
- A file put into `cards/` while the program is running is not copied again on import: it is opened where it is.
- **New Card** (`Ctrl+N`) is saved into the library on the first Save; the file name comes from the character name. Renaming the character later does not rename the file.
- **Save** (`Ctrl+S`) and **Save All** (`Ctrl+Shift+S`) write to the library without asking for a file name. A card cannot be saved without a name.
- **Export** (`Ctrl+E`) writes a copy of the card, as shown in the editor (including unsaved edits), to any folder outside the library. The library card is not changed.
- **Delete** (or the `Delete` key on the card grid) removes the card file from the library after confirmation. Files you imported from are not affected.

The `cards/` folder is local and is not part of the repository. To back up your cards, copy this folder.

### Card formats

- **V2 / V3** (`spec` + `data`): fields are written to `data`. If the file also keeps a copy at the root, as SillyTavern exports do, the root copy is updated too. Creator's Notes at the root is `creatorcomment`.
- **V1** (plain fields at the root): when you save changes, a V2 `data` block is added so that Alternate Greetings and Created by are stored where SillyTavern reads them. Root fields stay in place.
- PNG cards are not supported. Export the card from SillyTavern as JSON.

### What is kept unchanged

Fields that are not shown in the editor are never touched: Character's Note, embedded lorebook (`character_book`), linked World Info, regex scripts, all `extensions`, V3 fields, and any unknown keys.

A field is written back only if you changed it. A card saved without edits is not modified. Edited text keeps the line endings of the original field (for example Windows `\r\n`) and special spaces such as no-break spaces. Alternate greetings you did not edit are saved exactly as they were.

The file keeps its formatting: indentation, newline at the end, line endings and BOM are the same as in the imported file, so a diff shows only the lines you changed. New cards are written like SillyTavern does (4-space indent).

## License

MIT. You may freely use and modify this program.
