#!/usr/bin/env python3
"""Decide whether configured patch bundles differ from the last release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent

# Config fields that only affect the README and Obtainium links, not what gets built:
# changing them must not trigger a rebuild.
DISPLAY_ONLY_FIELDS = {"title", "package"}


def github_json(url: str) -> dict | list:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def release_for(entry: dict) -> dict:
    user, repo = entry["user"], entry["repo"]
    tag = entry.get("tag", "latest")
    api = f"https://api.github.com/repos/{user}/{repo}/releases"
    if tag == "latest":
        return github_json(f"{api}/latest")  # type: ignore[return-value]
    if tag == "prerelease":
        releases = github_json(api)
        prereleases = [release for release in releases if release.get("prerelease")]
        if not prereleases:
            raise RuntimeError(f"No prerelease found for {user}/{repo}")
        return max(prereleases, key=lambda release: release["created_at"])
    return github_json(f"{api}/tags/{tag}")  # type: ignore[return-value]


def source_state(source: str) -> list[dict]:
    entries = json.loads((ROOT / "sources" / f"{source}.json").read_text())
    state = []
    for entry in entries[1:]:
        if entry.get("repo") == "morphe-cli":
            continue
        release = release_for(entry)
        assets = [
            {
                "id": asset["id"],
                "name": asset["name"],
                "size": asset["size"],
                "updated_at": asset["updated_at"],
            }
            for asset in release.get("assets", [])
            if asset["name"].endswith(".mpp")
        ]
        state.append(
            {
                "repository": f"{entry['user']}/{entry['repo']}",
                "requested_tag": entry.get("tag", "latest"),
                "release_id": release["id"],
                "tag_name": release["tag_name"],
                "published_at": release.get("published_at"),
                "assets": assets,
            }
        )
    return state


def write_output(name: str, value: str) -> None:
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a") as file:
            file.write(f"{name}={value}\n")
    else:
        print(f"{name}={value}")


def entries_hash(entries: list[dict]) -> str:
    """Hash of a source's build entries, ignoring display-only fields."""
    build_entries = [
        {key: value for key, value in entry.items() if key not in DISPLAY_ONLY_FIELDS}
        for entry in entries
    ]
    return hashlib.sha256(
        json.dumps(build_entries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    config = json.loads((ROOT / "patch-config.json").read_text())
    entries_by_source: dict[str, list[dict]] = {}
    for entry in config["patch_list"]:
        entries_by_source.setdefault(entry["source"], []).append(entry)

    current = {
        "sources": {
            source: {
                "entries_sha256": entries_hash(entries),
                "bundles": source_state(source),
            }
            for source, entries in sorted(entries_by_source.items())
        },
    }

    try:
        previous = json.loads(args.previous.read_text())
    except FileNotFoundError:
        previous = {"sources": {}}
    except json.JSONDecodeError:
        previous = {"sources": {}}

    args.state.write_text(json.dumps(current, indent=2) + "\n")
    previous_sources = previous.get("sources", {})
    sources_to_build = [
        source
        for source, state in current["sources"].items()
        if args.force or state != previous_sources.get(source)
    ]
    should_build = bool(sources_to_build)
    write_output("should_build", str(should_build).lower())
    write_output("sources_to_build", ",".join(sources_to_build))
    print(
        f"Sources requiring a build: {', '.join(sources_to_build)}"
        if should_build
        else "Patch state is unchanged."
    )


if __name__ == "__main__":
    try:
        main()
    except (HTTPError, KeyError, RuntimeError, TimeoutError) as error:
        print(f"Unable to determine patch state: {error}", file=sys.stderr)
        raise SystemExit(1)
