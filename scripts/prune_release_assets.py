#!/usr/bin/env python3
"""Keep only the newest build of each app on its GitHub release(s).

Patched APKs are named ``<app>-<arch>-<source>-v<version>-<YYYYMMDD>.apk``. In every
release, for each (app, source) pair the assets with the newest date are kept and
older ones are deleted. With ``--built``, the APKs just published are also
authoritative: any other asset of an app they cover is deleted, even when it has the
same date (e.g. a universal build replaced by an arm64 one the same day). Assets that
do not follow the naming pattern (state files, notes) are left alone.

By default every release is checked (``--tag`` limits it to one). Publishing already
replaces an app's asset on its own release (scripts/publish_releases.py); this is for
manual clean-ups. Uses the ``gh`` CLI, which picks the repository from the checkout.
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
    parser.add_argument("--tag", help="check only this release (default: all releases)")
    parser.add_argument("--built", nargs="*", default=[], metavar="APK",
                        help="file names just published; other assets of the same apps are removed")
    parser.add_argument("--dry-run", action="store_true", help="only list what would be deleted")
    args = parser.parse_args()

    if args.tag:
        releases = [json.loads(gh_api(f"repos/{{owner}}/{{repo}}/releases/tags/{args.tag}"))]
    else:
        releases = json.loads(gh_api("repos/{owner}/{repo}/releases?per_page=100"))
    found = False
    for release in releases:
        for asset in stale_assets(release.get("assets", []), args.built):
            found = True
            print(f"{'Would delete' if args.dry_run else 'Deleting'} older build: {release['tag_name']}/{asset['name']}")
            if not args.dry_run:
                gh_api("-X", "DELETE", f"repos/{{owner}}/{{repo}}/releases/assets/{asset['id']}")
    if not found:
        print("Every release holds only the newest build of its app.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
