"""Simple JSON-file-based subscriber store."""

import json
import os
from typing import Optional

from config import SUBSCRIBERS_FILE


def _load() -> dict:
    if not os.path.exists(SUBSCRIBERS_FILE):
        return {"subscribers": {}}
    with open(SUBSCRIBERS_FILE, "r") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def add_subscriber(chat_id: int, source_filter: Optional[str] = None) -> bool:
    """Add a subscriber. Returns True if newly added, False if already existed."""
    data = _load()
    key = str(chat_id)
    if key in data["subscribers"]:
        data["subscribers"][key]["source_filter"] = source_filter
        _save(data)
        return False
    data["subscribers"][key] = {"source_filter": source_filter}
    _save(data)
    return True


def remove_subscriber(chat_id: int) -> bool:
    """Remove a subscriber. Returns True if removed, False if not found."""
    data = _load()
    key = str(chat_id)
    if key not in data["subscribers"]:
        return False
    del data["subscribers"][key]
    _save(data)
    return True


def get_all_subscribers() -> dict[int, dict]:
    """Return {chat_id: {source_filter: ...}} for all subscribers."""
    data = _load()
    return {int(k): v for k, v in data["subscribers"].items()}


def is_subscribed(chat_id: int) -> bool:
    data = _load()
    return str(chat_id) in data["subscribers"]
