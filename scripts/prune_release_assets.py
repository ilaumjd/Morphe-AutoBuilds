#!/usr/bin/env python3
"""Keep only the newest build of each app on a GitHub release.

Patched APKs are named ``<app>-<arch>-<source>-v<version>-<YYYYMMDD>.apk``. For
every (app, source) pair the assets with the newest date are kept and any older
ones are deleted. With ``--built``, the APKs just published are also
authoritative: any other asset of an app they cover is deleted, even when it has
the same date (e.g. a universal build replaced by an arm64 one the same day), so
the release never holds two versions of the same app. Assets that do not follow
the naming pattern (state files, notes) are left alone.

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


def stale_assets(assets: list[dict], built: list[str] = ()) -> list[dict]:
    """Return the assets that a newer build of their app has replaced."""
    newest: dict[tuple[str, str], str] = {}
    parsed = []
    for asset in assets:
        match = ASSET_NAME.match(asset["name"])
        if match:
            key = (match["app"], match["source"])
            parsed.append((key, match["date"], asset))
            newest[key] = max(newest.get(key, ""), match["date"])

    built_names = set(built)
    built_keys = set()
    for name in built_names:
        match = ASSET_NAME.match(name)
        if match:
            built_keys.add((match["app"], match["source"]))

    return [
        asset
        for key, date, asset in parsed
        if date < newest[key] or (key in built_keys and asset["name"] not in built_names)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default="latest", help="release tag (default: latest)")
    parser.add_argument("--built", nargs="*", default=[], metavar="APK",
                        help="file names just published; other assets of the same apps are removed")
    parser.add_argument("--dry-run", action="store_true", help="only list what would be deleted")
    args = parser.parse_args()

    release = json.loads(gh_api(f"repos/{{owner}}/{{repo}}/releases/tags/{args.tag}"))
    stale = stale_assets(release.get("assets", []), args.built)
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
