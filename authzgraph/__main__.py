"""CLI. inspect already works; check is the piece to implement."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from authzgraph.store import StoreError, load_caveats, load_namespace, load_tuples


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="authzgraph")
    sub = p.add_subparsers(dest="cmd", required=True)
    ins = sub.add_parser("inspect", help="load tuples and namespace and print a summary")
    ins.add_argument("--namespace", required=True)
    ins.add_argument("--tuples", required=True)
    ins.add_argument("--caveats", required=False)
    chk = sub.add_parser("check", help="evaluate a relationship query")
    chk.add_argument("--namespace", required=True)
    chk.add_argument("--tuples", required=True)
    chk.add_argument("--caveats", required=False)
    chk.add_argument("--query", required=True, help="object#relation@subject, e.g. doc:budget#viewer@user:alice")
    chk.add_argument("--context", required=False, help="JSON object or @path")
    chk.add_argument("--max-depth", type=int, default=32)
    chk.add_argument("--report", required=True)
    return p


def _read_context(value: str | None) -> dict:
    if not value:
        return {}
    text = value
    if value.startswith("@"):
        text = Path(value[1:]).read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("context must be an object")
    return data


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        namespace = load_namespace(args.namespace)
        tuples = load_tuples(args.tuples)
        caveats = load_caveats(getattr(args, "caveats", None))
    except (StoreError, OSError) as exc:
        print(f"failed to load inputs: {exc}", file=sys.stderr)
        return 2

    if args.cmd == "inspect":
        print(json.dumps({
            "types": list((namespace.get("types") or {}).keys()),
            "tuple_count": len(tuples),
            "tuples": [t.as_str() for t in tuples],
            "caveat_defs": list(caveats.keys()),
        }, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "check":
        from authzgraph.engine import check
        from authzgraph.store import parse_tuple

        try:
            q = parse_tuple(args.query)
            context = _read_context(args.context)
        except (StoreError, ValueError, OSError, json.JSONDecodeError) as exc:
            print(f"bad query or context: {exc}", file=sys.stderr)
            return 2
        query = args.query
        try:
            report = check(namespace, tuples, caveats, query, context, args.max_depth)
        except NotImplementedError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        decision = str(report.get("decision", "")).lower()
        if decision == "allow":
            return 0
        if decision == "deny":
            return 1
        print("report is missing a decision of allow or deny", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
