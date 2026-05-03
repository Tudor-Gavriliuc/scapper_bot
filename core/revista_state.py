from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

STATE_PATH = Path("data/revista_post_state.json")


def _load_state() -> Dict:
    if not STATE_PATH.exists():
        return {}

    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: Dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def was_posted(source: str, link: str) -> bool:
    state = _load_state()
    source_state = state.get(source) or {}
    return (source_state.get("last_link") or "") == (link or "")


def mark_posted(source: str, link: str) -> None:
    state = _load_state()
    source_state = state.get(source) or {}
    source_state["last_link"] = link or ""
    state[source] = source_state
    _save_state(state)
