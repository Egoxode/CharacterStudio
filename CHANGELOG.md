# Changelog

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
