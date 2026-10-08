#!/usr/bin/env python3
"""Publish every patched APK as its own GitHub release.

Each app has one release, tagged with the app name (e.g. ``tiktok``) and titled
``<App title> <version>`` (e.g. ``TikTok 47.1.4``). Its only asset is that app's
newest APK, replaced on every update. This lets Obtainium read a real version from
the title and compare it with the installed one.

Patched APKs are named ``<app>-<arch>-<source>-v<version>-<YYYYMMDD>.apk``.
The patch state is kept on a prerelease tagged ``state`` (Obtainium skips
prereleases).

Works with the old ``gh`` in the runner image (2.4.0): releases are edited through
``gh api`` because ``gh release edit`` does not exist there. Run from a checkout.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSET = re.compile(
    r"^(?P<app>[^-]+)-(?P<arch>arm64-v8a|armeabi-v7a|universal)-(?P<source>[^-]+)"
    r"-v(?P<version>.+)-(?P<date>\d{8})\.apk$"
)
STATE_TAG = "state"
API = "repos/{owner}/{repo}/releases"


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def get_release(tag: str) -> dict | None:
    try:
        return json.loads(gh("api", f"{API}/tags/{tag}"))
    except subprocess.CalledProcessError:
        return None


def titles(app: str, source: str) -> tuple[str, str]:
    """Display name of the app and of its patch source."""
    config = json.loads((ROOT / "patch-config.json").read_text())["patch_list"]
    entry = next((e for e in config if e["app_name"] == app), {})
    first = json.loads((ROOT / "sources" / f"{source}.json").read_text())[0]
    return entry.get("title") or app, first.get("title") or first["name"]


def set_details(release_id: int, title: str, body: str, prerelease: bool | None = None) -> None:
    args = ["api", "-X", "PATCH", f"{API}/{release_id}", "-f", f"name={title}", "-f", f"body={body}"]
    if prerelease is not None:
        args += ["-F", f"prerelease={str(prerelease).lower()}"]
    gh(*args)


def drop_other_assets(release: dict, keep: set[str], dry: bool) -> None:
    for asset in release.get("assets", []):
        if asset["name"] not in keep:
            print(f"  deleting older asset {asset['name']}")
            if not dry:
                gh("api", "-X", "DELETE", f"{API}/assets/{asset['id']}")


def publish_apk(apk: Path, dry: bool) -> None:
    match = ASSET.match(apk.name)
    if not match:
        raise SystemExit(f"{apk.name} does not look like a patched APK")
    app, version = match["app"], match["version"]
    title, source_title = titles(app, match["source"])
    release_title = f"{title} {version}"
    body = (
        f"{title} {version} ({match['arch']}), patched with {source_title} on "
        f"{match['date'][:4]}-{match['date'][4:6]}-{match['date'][6:]}.\n\n"
        "This release holds only the newest build of this app; it is replaced on every update."
    )
    print(f"{app}: {release_title}  <-  {apk.name}")
    if dry:
        return
    release = get_release(app)
    if release is None:
        gh("release", "create", app, str(apk), "--title", release_title, "--notes", body)
    else:
        gh("release", "upload", app, str(apk), "--clobber")
        set_details(release["id"], release_title, body)
    release = get_release(app)
    if not release or apk.name not in {a["name"] for a in release.get("assets", [])}:
        raise SystemExit(f"{apk.name} is not on release {app} after upload")
    drop_other_assets(release, {apk.name}, dry)


def publish_state(state: Path, dry: bool) -> None:
    print(f"{STATE_TAG}: patch state  <-  {state}")
    if dry:
        return
    body = "Internal: saved patch state of the local runner. Not an app release."
    release = get_release(STATE_TAG)
    if release is None:
        gh("release", "create", STATE_TAG, str(state), "--title", "Patch state", "--notes", body, "--prerelease")
    else:
        gh("release", "upload", STATE_TAG, str(state), "--clobber")
        set_details(release["id"], "Patch state", body, prerelease=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", type=Path, help="build-results.json: publish the APKs built in that run")
    parser.add_argument("--apk", nargs="*", default=[], type=Path, help="publish these APK files")
    parser.add_argument("--state", type=Path, help="patch state file to store on the 'state' release")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    apks = list(args.apk)
    if args.results:
        built = json.loads(args.results.read_text()).get("built", [])
        apks += [Path(p) for p in built if p.endswith(".apk") and Path(p).is_file()]
    for apk in apks:
        publish_apk(apk, args.dry_run)
    if args.state:
        publish_state(args.state, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
