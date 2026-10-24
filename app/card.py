"""Character card model.

Only the fields listed in FIELDS are edited. Everything else in the file
(extensions, character_book, Personality, prompts, V3 fields, unknown keys)
is kept exactly as loaded. A field is written back only if the user changed it.
"""
import copy

# field id, key inside "data", key at the root (V1 / SillyTavern mirror) or None
FIELDS = [
    ("name", "name", "name"),
    ("description", "description", "description"),
    ("scenario", "scenario", "scenario"),
    ("first_mes", "first_mes", "first_mes"),
    ("alternate_greetings", "alternate_greetings", None),
    ("mes_example", "mes_example", "mes_example"),
    ("personality", "personality", "personality"),
    ("system_prompt", "system_prompt", None),
    ("post_history_instructions", "post_history_instructions", None),
    ("creator", "creator", None),
    ("creator_notes", "creator_notes", "creatorcomment"),
    ("tags", "tags", "tags"),
]
LIST_FIELDS = {"alternate_greetings", "tags"}

# Fields a V2 card must have in "data" (Character Card V2 spec).
V2_DATA_DEFAULTS = {
    "name": "",
    "description": "",
    "personality": "",
    "scenario": "",
    "first_mes": "",
    "mes_example": "",
    "creator_notes": "",
    "system_prompt": "",
    "post_history_instructions": "",
    "alternate_greetings": [],
    "tags": [],
    "creator": "",
    "character_version": "",
    "extensions": {},
}
# V1 root keys that map to V2 "data" keys when an old card is upgraded.
V1_TO_V2 = {
    "name": "name",
    "description": "description",
    "personality": "personality",
    "scenario": "scenario",
    "first_mes": "first_mes",
    "mes_example": "mes_example",
    "creatorcomment": "creator_notes",
    "tags": "tags",
}


def _text(value):
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)


def _str_list(value):
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    if isinstance(value, (list, tuple)):
        return [_text(x) for x in value if x is not None]
    return []


def _norm(value):
    """Compare values ignoring Windows line endings (the text editor turns \\r\\n into \\n)."""
    if isinstance(value, list):
        return [_norm(x) for x in value]
    return value.replace("\r\n", "\n").replace("\r", "\n") if isinstance(value, str) else value


def _uses_crlf(values) -> bool:
    """True if the original text uses Windows line endings (\r\n) and never a bare \n."""
    texts = [v for v in values if isinstance(v, str) and "\n" in v]
    return bool(texts) and all(v.count("\n") == v.count("\r\n") for v in texts)


def _keep_style(new_value, old_value):
    """Write an edited value in the original line-ending style.
    List items whose text did not change are kept exactly as they were in the file."""
    if isinstance(new_value, list):
        old_items = old_value if isinstance(old_value, list) else []
        exact = {}
        for item in old_items:
            if isinstance(item, str):
                exact.setdefault(_norm(item), item)
        crlf = _uses_crlf(old_items)
        return [exact.get(_norm(x), x.replace("\n", "\r\n") if crlf else x) for x in new_value]
    if isinstance(new_value, str) and _uses_crlf([old_value]):
        return _norm(new_value).replace("\n", "\r\n")
    return new_value


def is_card(obj) -> bool:
    if not isinstance(obj, dict):
        return False
    if str(obj.get("spec", "")).startswith("chara_card"):
        return isinstance(obj.get("data"), dict)
    if isinstance(obj.get("data"), dict) and "name" in obj["data"] and "first_mes" in obj["data"]:
        return True
    # V1: plain fields at the root. A lorebook has "entries" and no first_mes.
    return "name" in obj and "first_mes" in obj and "entries" not in obj


def card_format(obj) -> str:
    spec = str(obj.get("spec", "")) if isinstance(obj, dict) else ""
    if spec == "chara_card_v3":
        return "V3"
    if spec == "chara_card_v2" or isinstance(obj.get("data"), dict):
        return "V2"
    return "V1"


def read_values(raw: dict) -> dict:
    data = raw.get("data") if isinstance(raw.get("data"), dict) else None
    values = {}
    for field, data_key, root_key in FIELDS:
        if data is not None and data_key in data:
            v = data[data_key]
        elif root_key and root_key in raw:
            v = raw[root_key]
        else:
            v = [] if field in LIST_FIELDS else ""
        values[field] = _str_list(v) if field in LIST_FIELDS else _text(v)
    return values


def upgrade_to_v2(raw: dict) -> dict:
    """Add a V2 "data" block to a V1 card. Root fields stay as they are."""
    data = copy.deepcopy(V2_DATA_DEFAULTS)
    for root_key, data_key in V1_TO_V2.items():
        if root_key in raw:
            v = raw[root_key]
            data[data_key] = _str_list(v) if data_key == "tags" else _text(v)
    raw["spec"] = "chara_card_v2"
    raw["spec_version"] = "2.0"
    raw["data"] = data
    return raw


def new_card_raw(name="New Character") -> dict:
    """A new V2 card in the layout SillyTavern uses: V1 mirror at the root plus "data"."""
    raw = {
        "name": name,
        "description": "",
        "personality": "",
        "scenario": "",
        "first_mes": "",
        "mes_example": "",
        "creatorcomment": "",
        "tags": [],
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": copy.deepcopy(V2_DATA_DEFAULTS),
    }
    raw["data"]["name"] = name
    return raw


class Card:
    def __init__(self, raw: dict, path=None, is_new=False, style=None):
        self.raw = raw
        self.style = style  # file formatting (indent, BOM...), see storage.detect_style
        self.path = path
        self.is_new = is_new
        self.saved = read_values(raw)
        self.values = copy.deepcopy(self.saved)

    @property
    def format(self) -> str:
        return card_format(self.raw)

    def changed_fields(self):
        return [f for f, _, _ in FIELDS if _norm(self.values[f]) != _norm(self.saved[f])]

    @property
    def dirty(self) -> bool:
        return self.is_new or bool(self.changed_fields())

    def set(self, field, value):
        self.values[field] = list(value) if field in LIST_FIELDS else _text(value)

    def to_json(self) -> dict:
        out = copy.deepcopy(self.raw)
        changed = self.changed_fields()
        if not changed:
            return out
        if not isinstance(out.get("data"), dict):
            upgrade_to_v2(out)
        data = out["data"]
        for field, data_key, root_key in FIELDS:
            if field not in changed:
                continue
            old = data.get(data_key, out.get(root_key) if root_key else None)
            value = _keep_style(copy.deepcopy(self.values[field]), old)
            data[data_key] = value
            # Mirror to the root only where the file already keeps a root copy (SillyTavern layout).
            if root_key and root_key in out:
                out[root_key] = copy.deepcopy(value)
        return out

    def mark_saved(self, raw: dict, path):
        self.raw = raw
        self.path = path
        self.is_new = False
        self.saved = read_values(raw)
        self.values = copy.deepcopy(self.saved)
