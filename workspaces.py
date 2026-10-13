"""Keep uploaded references, controls and results beyond a mobile page reload."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import threading
import uuid

ROOT = Path(__file__).resolve().parent
FIELDS = ("text", "voice", "reference", "blend_voice", "blend_amount", "emotion", "emotion_amount",
          "seed", "temperature", "rate", "accurate")
LOCK = threading.RLock()


def valid_token(token):
    return isinstance(token, str) and bool(re.fullmatch(r"[0-9a-f]{32}", token))


def folder(token):
    if not valid_token(token):
        raise ValueError("Reload the page to initialize your workspace.")
    result = ROOT / "jobs" / "workspaces" / token
    result.mkdir(parents=True, exist_ok=True)
    return result


def read(token):
    with LOCK:
        file = folder(token) / "state.json"
        if not file.is_file():
            return {}
        try:
            return json.loads(file.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {}


def patch(token, values):
    with LOCK:
        state = read(token)
        state.update(values)
        destination = folder(token) / "state.json"
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(destination)
        return state


def persist_reference(token, source):
    if not source:
        return None
    source = Path(source)
    if not source.is_file():
        raise ValueError("Audio upload is incomplete. Upload again and wait for its preview.")
    destination = folder(token) / ("reference-" + hashlib.sha256(source.read_bytes()).hexdigest()[:16] + source.suffix.lower())
    if source.resolve() != destination.resolve() and not destination.exists():
        shutil.copy2(source, destination)
    return str(destination)


def own_file(token, value):
    if not value:
        return None
    file = Path(value).resolve()
    permitted = (file.is_relative_to(folder(token).resolve()) or
                 file.is_relative_to((ROOT / "outputs").resolve()))
    return str(file) if permitted and file.is_file() else None


def initialize(token):
    token = token if valid_token(token) else uuid.uuid4().hex
    return token, read(token)
