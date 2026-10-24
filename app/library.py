"""Card library: the program keeps its own copies of cards in the cards/ folder next to it.

Files from elsewhere are imported (copied byte for byte) and never touched again.
"""
import os
import shutil
from pathlib import Path


def default_library_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "cards"


def safe_stem(name: str) -> str:
    """File name (without extension) from a character name; characters Windows forbids are removed."""
    safe = "".join(c for c in name if c not in '\\/:*?"<>|' and ord(c) >= 32).strip().rstrip(".")
    return safe or "character"


def unique_path(folder: Path, stem: str, taken=()) -> Path:
    """<stem>.json, or <stem> (2).json, (3)... if the name is used on disk or in `taken`."""
    taken = {os.path.normcase(str(Path(p).resolve())) for p in taken}

    def free(p: Path) -> bool:
        return not p.exists() and os.path.normcase(str(p.resolve())) not in taken

    path = folder / f"{stem}.json"
    n = 2
    while not free(path):
        path = folder / f"{stem} ({n}).json"
        n += 1
    return path


def is_inside(path, folder) -> bool:
    try:
        Path(path).resolve().relative_to(Path(folder).resolve())
        return True
    except ValueError:
        return False


def import_copy(src, folder: Path, taken=()) -> Path:
    """Copy a card file into the library under its own name (numbered if taken). Returns the new path."""
    target = unique_path(folder, Path(src).stem, taken)
    shutil.copyfile(src, target)
    return target
