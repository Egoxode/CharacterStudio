# Changelog

## 1.0.7

### Fixed
- A message box (a question, a warning, an error) had dark patches behind its text and icon: the dialog had a lighter background than the widgets inside it. Dialogs now have the same background as the main window.

## 1.0.6

### Fixed
- A file dragged into the window with Shift (or Alt, Ctrl+Shift) was accepted as "moved", and Windows Explorer could then delete the original. A dropped file is now always accepted as "copied", as in Lorebook Studio and Lorebook Organizer.
- A file dropped on a message box of the program was imported too. Now only drops on the main window are.
- Export: a name with another extension (`my.card`) was saved without `.json`. Now `.json` is added (`my.card.json`).
- A file put into `cards/` while the program was running was copied into the same folder a second time on import (`name (2).json`). Now it is opened where it is.
- The question on closing showed an empty line for a card whose name is only spaces; now it shows "Unnamed", as elsewhere.

### Changed
- Removed unused code.

## 1.0.5

### Changed
- Errors are written to `error.log` and shown in a message box however the program was started: before, only `CharacterStudio.pyw` did this, and with `python main.py` an error was only printed to the console, which may close at once. In the console the error is still printed too. The error handling is in `error_log.py`, used by both `main.py` and `CharacterStudio.pyw`.

## 1.0.4

### Added
- Advanced tab (after Examples): Personality, System Prompt and Post-History Instructions, each with a character and token counter. In SillyTavern they are Personality summary, Main Prompt and Post-History Instructions in Advanced Definitions. As with the other fields, only what you change is written; Personality is also written to the root copy if the card has one.

## 1.0.3

### Changed
- Text fields grow with the window instead of leaving empty space below them: Description and Scenario share the Character tab (2 : 1), First Message fills the Greetings tab, Examples of Dialogue and Creator's Notes fill their tabs. They never get smaller than before.
- Tags is a field of three lines with word wrap, so a long tag list is visible. Enter does nothing there, Tab moves to the next field, and lines pasted from elsewhere become separate tags.

## 1.0.2

### Fixed
- A card with `NaN` or `Infinity` (not valid JSON; SillyTavern cannot read it) was imported and saved back unchanged. Now it is skipped with a message, like other broken files.

## 1.0.1

### Fixed
- The program could crash (Segmentation fault) on exit after cards were edited.

## 1.0

First release.

- Edit Name, Description, Scenario, First Message, Alternate Greetings, Examples of Dialogue, Created by, Tags, Creator's Notes.
- Own card library in `cards/`, opened on start. Import files, a folder, or drag and drop (also onto a text field); originals are copied and never changed.
- Avatar grid, always sorted by name.
- Export a copy of a card to any folder; delete a card from the library.
- All other fields of the card are kept unchanged; only edited fields are written.
- SillyTavern layout (root copy + `data`) and pure V2 / V3 cards are saved in their own layout. V1 cards get a V2 `data` block when saved with changes.
- New cards in Character Card V2 format.
- The file keeps its formatting (indent, final newline, line endings, BOM); edited text keeps its line endings and no-break spaces.
- Unsaved changes warning when closing the program.
