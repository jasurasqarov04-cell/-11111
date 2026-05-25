"""Простое хранилище выбранного языка по user_id (JSON-файл рядом с ботом)."""
import json
import os
import threading
from typing import Optional

LANG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".user_lang.json"
)
_lock = threading.Lock()


def _load() -> dict:
    if not os.path.isfile(LANG_FILE):
        return {}
    try:
        with open(LANG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def get_lang(user_id: int) -> Optional[str]:
    if user_id is None:
        return None
    data = _load()
    val = data.get(str(user_id))
    return val if isinstance(val, str) and val else None


def set_lang(user_id: int, lang: str) -> None:
    if user_id is None or not lang:
        return
    with _lock:
        data = _load()
        data[str(user_id)] = lang
        try:
            with open(LANG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError:
            pass
