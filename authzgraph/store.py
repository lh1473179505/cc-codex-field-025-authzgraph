"""Load relationship tuples and a namespace config."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class StoreError(Exception):
    pass


@dataclass
class Caveat:
    name: str
    expr: dict[str, Any]


@dataclass
class Tuple:
    object_type: str
    object_id: str
    relation: str
    subject_type: str
    subject_id: str
    subject_relation: str | None
    caveat: Caveat | None

    def object_key(self) -> str:
        return f"{self.object_type}:{self.object_id}"

    def subject_key(self) -> str:
        if self.subject_relation:
            return f"{self.subject_type}:{self.subject_id}#{self.subject_relation}"
        return f"{self.subject_type}:{self.subject_id}"

    def as_str(self) -> str:
        cav = f" [{self.caveat.name}]" if self.caveat else ""
        return f"{self.object_key()}#{self.relation}@{self.subject_key()}{cav}"


def parse_tuple(line: str) -> Tuple:
    text = line.strip()
    if not text or text.startswith("#"):
        raise StoreError("empty tuple")
    caveat = None
    if " [" in text and text.endswith("]"):
        text, cav = text.rsplit(" [", 1)
        name = cav[:-1]
        caveat = Caveat(name=name, expr={})
    try:
        left, subject = text.split("@", 1)
        obj, relation = left.split("#", 1)
        object_type, object_id = obj.split(":", 1)
    except ValueError as exc:
        raise StoreError(f"bad tuple: {line!r}") from exc
    subject_relation = None
    if "#" in subject:
        subject, subject_relation = subject.split("#", 1)
    try:
        subject_type, subject_id = subject.split(":", 1)
    except ValueError as exc:
        raise StoreError(f"bad subject: {line!r}") from exc
    return Tuple(object_type, object_id, relation, subject_type, subject_id, subject_relation or None, caveat)


def load_tuples(path: str | Path) -> list[Tuple]:
    out: list[Tuple] = []
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise StoreError(str(exc)) from exc
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        out.append(parse_tuple(line))
    return out


def load_namespace(path: str | Path) -> dict[str, Any]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StoreError(str(exc)) from exc
    if not isinstance(raw, dict) or "types" not in raw:
        raise StoreError("namespace must have types")
    return raw


def load_caveats(path: str | Path | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StoreError(str(exc)) from exc
    if not isinstance(raw, dict):
        raise StoreError("caveats must be an object")
    return raw
