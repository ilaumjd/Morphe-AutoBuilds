#!/usr/bin/env python3
"""Persist source state only for sources whose configured entries all built."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"sources": {}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()

    previous = load(args.previous)
    candidate = load(args.candidate)
    results = load(args.results)
    successful = set(results.get("successful_sources", []))

    merged = {"sources": dict(previous.get("sources", {}))}
    for source in successful:
        if source in candidate.get("sources", {}):
            merged["sources"][source] = candidate["sources"][source]

    args.candidate.write_text(json.dumps(merged, indent=2) + "\n")
    print(f"Recorded patch state for: {', '.join(sorted(successful)) or 'none'}")


if __name__ == "__main__":
    main()
