#!/usr/bin/env python3
"""Delete patched builds that are no longer the one published for their app.

apks/patched keeps every build the pipeline makes. For each app that has a release on
GitHub, only the APK attached to that release is kept; older builds of the same app,
together with their ``.idsig`` signature and ``.patches.json`` report, are deleted.
Builds of apps that have no release yet (for example one just built and not published)
are never touched. Originals in apks/original are never touched either.

    python scripts/clean_patched.py --dry-run     # list what would be deleted
    python scripts/clean_patched.py               # delete it

Needs the ``gh`` CLI, run from a checkout of the repository.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.paths import PATCHED_APKS_DIR  # noqa: E402

ASSET = re.compile(
    r"^(?P<app>[^-]+)-(?P<arch>arm64-v8a|armeabi-v7a|universal)-(?P<source>[^-]+)"
    r"-v(?P<version>.+)-(?P<date>\d{8})\.apk$"
)
SUFFIXES = (".apk.idsig", ".patches.json", ".apk")


def published_assets() -> set[str]:
    out = subprocess.run(
        ["gh", "api", "repos/{owner}/{repo}/releases?per_page=100"],
        check=True, capture_output=True, text=True,
    ).stdout
    return {
        asset["name"]
        for release in json.loads(out)
        for asset in release.get("assets", [])
        if asset["name"].endswith(".apk")
    }


def build_name(path: Path) -> str | None:
    """The ``<...>.apk`` build a file belongs to (the APK itself, its .idsig or report)."""
    for suffix in SUFFIXES:
        if path.name.endswith(suffix):
            return path.name[: -len(suffix)] + ".apk"
    return None


def stale_files(directory: Path, published: set[str]) -> tuple[list[Path], list[str]]:
    """Files to delete, and the apps skipped because they have no release."""
    published_apps = {m["app"] for name in published if (m := ASSET.match(name))}
    stale, unpublished = [], set()
    for path in sorted(directory.iterdir()):
        build = build_name(path) if path.is_file() else None
        match = ASSET.match(build) if build else None
        if not match:
            continue
        if match["app"] not in published_apps:
            unpublished.add(match["app"])
        elif build not in published:
            stale.append(path)
    return stale, sorted(unpublished)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="only list what would be deleted")
    parser.add_argument("--dir", type=Path, default=PATCHED_APKS_DIR, help="patched builds folder")
    args = parser.parse_args()

    published = published_assets()
    if not published:
        print("No published APKs found on the releases; refusing to delete anything.", file=sys.stderr)
        return 1
    stale, unpublished = stale_files(args.dir, published)
    total = 0
    for path in stale:
        total += path.stat().st_size
        print(f"{'Would delete' if args.dry_run else 'Deleting'} {path.name}")
        if not args.dry_run:
            path.unlink()
    if unpublished:
        print(f"Left alone (no release yet): {', '.join(unpublished)}")
    print(f"{len(stale)} file(s), {total / 1048576:.0f} MB {'would be ' if args.dry_run else ''}deleted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
