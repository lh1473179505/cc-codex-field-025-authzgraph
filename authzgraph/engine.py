"""Authorization check. Not implemented in this snapshot."""

from __future__ import annotations

from typing import Any

from authzgraph.store import Tuple


def check(
    namespace: dict[str, Any],
    tuples: list[Tuple],
    caveats: dict[str, dict[str, Any]],
    query: str,
    context: dict[str, Any],
    max_depth: int,
) -> dict[str, Any]:
    raise NotImplementedError("check is not implemented in this snapshot")
