import json
import os
import re
import tempfile

BOM = b"\xef\xbb\xbf"

# How SillyTavern writes card JSON: 4-space indent, no newline at the end of the file.
DEFAULT_STYLE = {"indent": 4, "separators": None, "newline": "\n", "trailing_newline": False,
                 "bom": False, "ensure_ascii": False}


def _reject_constant(name):
    # Python читает NaN/Infinity, но это не JSON: SillyTavern такой файл не откроет.
    raise ValueError(f"{name} is not a valid JSON value")


def read_json_file(path):
    """Load JSON and remember how the file is formatted, so it can be written back the same way."""
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8-sig")
    obj = json.loads(text, parse_constant=_reject_constant)
    return obj, detect_style(text, obj, raw.startswith(BOM))


def detect_style(text, obj, bom=False):
    style = dict(DEFAULT_STYLE)
    style["bom"] = bom
    style["newline"] = "\r\n" if "\r\n" in text else "\n"
    style["trailing_newline"] = text.endswith("\n")
    body = text.rstrip("\r\n")
    # \u escapes for non-ASCII characters and no raw non-ASCII text: the file was written in ASCII mode.
    style["ensure_ascii"] = text.isascii() and re.search(r"\\u(?!00[01][0-9a-fA-F])[0-9a-fA-F]{4}", text) is not None
    if "\n" not in body:
        style["indent"] = None
        style["separators"] = (",", ":")
        for seps in ((",", ":"), (", ", ": ")):
            if json.dumps(obj, ensure_ascii=style["ensure_ascii"], separators=seps) == body:
                style["separators"] = seps
                break
        return style
    second = body.split("\n")[1].rstrip("\r")
    ws = second[:len(second) - len(second.lstrip())]
    style["indent"] = "\t" if ws.startswith("\t") else (len(ws) or 2)
    return style


def dump_json(obj, style=None) -> bytes:
    style = style or DEFAULT_STYLE
    if style["indent"] is None:
        text = json.dumps(obj, ensure_ascii=style["ensure_ascii"], separators=style["separators"] or (",", ":"))
    else:
        text = json.dumps(obj, ensure_ascii=style["ensure_ascii"], indent=style["indent"])
    if style["newline"] == "\r\n":
        text = text.replace("\n", "\r\n")  # newlines inside strings are escaped, only layout changes
    if style["trailing_newline"]:
        text += style["newline"]
    data = text.encode("utf-8")
    return BOM + data if style["bom"] else data


def _default_file_mode() -> int:
    umask = os.umask(0)
    os.umask(umask)
    return 0o666 & ~umask


def save_bytes(path, data: bytes):
    """Atomic write: a temp file next to the target, then replace."""
    path = os.fspath(path)
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        # mkstemp создаёт файл с правами 0600 — сохраняем права исходного файла
        # (или обычные права по umask для нового файла).
        try:
            mode = os.stat(path).st_mode & 0o777
        except OSError:
            mode = _default_file_mode()
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def save_json(path, data, style=None):
    save_bytes(path, dump_json(data, style))

