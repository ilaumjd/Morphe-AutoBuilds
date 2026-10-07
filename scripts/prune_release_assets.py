#!/usr/bin/env python3
"""Keep only the newest build of each app on a GitHub release.

Patched APKs are named ``<app>-<arch>-<source>-v<version>-<YYYYMMDD>.apk``. For
every (app, source) pair the assets with the newest date are kept and any
older ones are deleted, so the release never holds two versions of the same
app. Assets that do not follow that pattern (state files, notes) are left alone.

Uses the ``gh`` CLI, which picks the repository from the current checkout.
"""
import argparse
import json
import re
import subprocess
import sys

ASSET_NAME = re.compile(
    r"^(?P<app>[^-]+)-(?P<arch>arm64-v8a|armeabi-v7a|universal)-(?P<source>[^-]+)"
    r"-v(?P<version>.+)-(?P<date>\d{8})\.apk$"
)


def gh_api(*args: str) -> str:
    return subprocess.run(["gh", "api", *args], check=True, capture_output=True, text=True).stdout


def stale_assets(assets: list[dict]) -> list[dict]:
    """Return the assets that are older than the newest build of their app."""
    newest: dict[tuple[str, str], str] = {}
    parsed = []
    for asset in assets:
        match = ASSET_NAME.match(asset["name"])
        if match:
            key = (match["app"], match["source"])
            parsed.append((key, match["date"], asset))
            newest[key] = max(newest.get(key, ""), match["date"])
    return [asset for key, date, asset in parsed if date < newest[key]]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default="latest", help="release tag (default: latest)")
    parser.add_argument("--dry-run", action="store_true", help="only list what would be deleted")
    args = parser.parse_args()

    release = json.loads(gh_api(f"repos/{{owner}}/{{repo}}/releases/tags/{args.tag}"))
    stale = stale_assets(release.get("assets", []))
    if not stale:
        print("Release holds only the newest build of each app.")
        return 0
    for asset in stale:
        print(f"{'Would delete' if args.dry_run else 'Deleting'} older build: {asset['name']}")
        if not args.dry_run:
            gh_api("-X", "DELETE", f"repos/{{owner}}/{{repo}}/releases/assets/{asset['id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
