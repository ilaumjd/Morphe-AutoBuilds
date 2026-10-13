#!/usr/bin/env python3
"""Send a summary of the daily run (patch bundle updates and builds) to ntfy.

Configuration (environment):
  NTFY_URL    ntfy server base URL on the VPS, e.g. https://ntfy.example.com
  NTFY_TOPIC  topic to publish to (default: morphe)
  NTFY_TOKEN  optional access token, sent as a Bearer token

If NTFY_URL is unset the summary is only printed. Delivery failures are reported on
stderr and never fail the pipeline.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


def load(path: Path | None) -> dict:
    if path is None:
        return {}
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def bundle_versions(state: dict) -> dict[tuple[str, str], str]:
    """Map (source, repository) -> tag_name of the bundle recorded in a state file."""
    versions: dict[tuple[str, str], str] = {}
    for source, info in state.get("sources", {}).items():
        for bundle in info.get("bundles", []):
            versions[(source, bundle["repository"])] = bundle["tag_name"]
    return versions


def build_message(previous: dict, candidate: dict, results: dict, downloads: dict) -> tuple[str, str]:
    old = bundle_versions(previous)
    new = bundle_versions(candidate)

    updates = []
    for key in sorted(new):
        if key not in old:
            updates.append(f"NEW {key[1]}: {new[key]} (source: {key[0]})")
        elif old[key] != new[key]:
            updates.append(f"{key[1]}: {old[key]} -> {new[key]} (source: {key[0]})")

    built = [Path(name).name for name in results.get("built", [])]
    failed = list(results.get("failed", [])) + [
        f"download: {item}" for item in downloads.get("failed", [])
    ]

    lines = []
    lines.append("Patch bundle updates:")
    lines += [f"- {u}" for u in updates] or ["- none"]
    if results:
        lines.append("")
        lines.append(f"Built APKs ({len(built)}):")
        lines += [f"- {name}" for name in built] or ["- none"]
    else:
        lines.append("")
        lines.append("No build this run.")
    if failed:
        lines.append("")
        lines.append(f"Failed ({len(failed)}):")
        lines += [f"- {item}" for item in failed]

    if failed:
        title, priority = f"Morphe: {len(failed)} build(s) failed", "high"
    elif built:
        title, priority = f"Morphe: {len(built)} APK(s) built", "default"
    else:
        title, priority = "Morphe: no updates", "low"
    return title, priority + "\n" + "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--results", type=Path, help="build-results.json, if the run built anything")
    parser.add_argument("--download-results", type=Path, help="download-results.json, if the run downloaded anything")
    args = parser.parse_args()

    title, rest = build_message(
        load(args.previous), load(args.candidate), load(args.results), load(args.download_results)
    )
    priority, body = rest.split("\n", 1)
    print(body)

    base = os.getenv("NTFY_URL", "").rstrip("/")
    if not base:
        print("NTFY_URL not set; skipping ntfy notification.", file=sys.stderr)
        return 0

    topic = os.getenv("NTFY_TOPIC", "morphe")
    headers = {"Title": title, "Priority": priority, "Tags": "package"}
    token = os.getenv("NTFY_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base}/{topic}", data=body.encode("utf-8"), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=30):
            pass
    except URLError as error:
        print(f"ntfy notification failed: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
