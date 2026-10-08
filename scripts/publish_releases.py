#!/usr/bin/env python3
"""Publish every patched APK as its own GitHub release, tagged with its version.

Each app has exactly one release. Its tag is ``v<version>`` (e.g. ``v47.1.4``), its
title ``<App title> <version>`` (e.g. ``TikTok 47.1.4``) and its only asset the app's
newest APK. Obtainium reads a GitHub release's tag as the version, so the tag is what
it compares with the installed version. Two apps never share a tag: if
``v<version>`` already belongs to another app the tag becomes ``v<version>-<app>``.

When an app updates, its existing release is retagged and renamed, the APK replaced and
older assets removed, so a release never holds two builds. An APK that is already on the
release (same SHA-256) is not uploaded again.

Patched APKs are named ``<app>-<arch>-<source>-v<version>-<YYYYMMDD>.apk``. The patch
state lives on a prerelease tagged ``state`` (Obtainium skips prereleases).

Works with the old ``gh`` in the runner image (2.4.0): releases are edited through
``gh api`` because ``gh release edit`` does not exist there. Run from a checkout.
"""
from __future__ import annotations

import argparse
import hashlib
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
API = "repos/{owner}/{repo}"


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def api(*args: str) -> dict | list | None:
    out = gh("api", *args)
    return json.loads(out) if out.strip() else None


def list_releases() -> list[dict]:
    return api(f"{API}/releases?per_page=100")  # type: ignore[return-value]


def app_of(release: dict) -> str | None:
    """The app whose APK a release holds, if any."""
    for asset in release.get("assets", []):
        match = ASSET.match(asset["name"])
        if match:
            return match["app"]
    return None


def titles(app: str, source: str) -> tuple[str, str]:
    """Display name of the app and of its patch source."""
    config = json.loads((ROOT / "patch-config.json").read_text())["patch_list"]
    entry = next((e for e in config if e["app_name"] == app), {})
    first = json.loads((ROOT / "sources" / f"{source}.json").read_text())[0]
    return entry.get("title") or app, first.get("title") or first["name"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def delete_asset(asset: dict) -> None:
    print(f"  deleting older asset {asset['name']}")
    api("-X", "DELETE", f"{API}/releases/assets/{asset['id']}")


def delete_release(release: dict) -> None:
    print(f"  deleting release {release['tag_name']}")
    api("-X", "DELETE", f"{API}/releases/{release['id']}")
    delete_tag(release["tag_name"])


def delete_tag(tag: str) -> None:
    try:
        api("-X", "DELETE", f"{API}/git/refs/tags/{tag}")
    except subprocess.CalledProcessError:
        pass  # already gone


def choose_tag(app: str, version: str, releases: list[dict]) -> str:
    tag = f"v{version}"
    owner = next((r for r in releases if r["tag_name"] == tag), None)
    if owner is not None and app_of(owner) not in (None, app):
        tag = f"v{version}-{app}"
    return tag


def publish_apk(apk: Path, dry: bool) -> None:
    match = ASSET.match(apk.name)
    if not match:
        raise SystemExit(f"{apk.name} does not look like a patched APK")
    app, version = match["app"], match["version"]
    title, source_title = titles(app, match["source"])
    release_title = f"{title} {version}"
    date = match["date"]
    body = (
        f"{title} {version} ({match['arch']}), patched with {source_title} on "
        f"{date[:4]}-{date[4:6]}-{date[6:]}.\n\n"
        "This release holds only the newest build of this app; it is replaced on every update."
    )
    releases = list_releases()
    tag = choose_tag(app, version, releases)
    mine = [r for r in releases if app_of(r) == app]
    print(f"{app}: {tag}  \"{release_title}\"  <-  {apk.name}")
    if dry:
        return

    if not mine:
        gh("release", "create", tag, str(apk), "--title", release_title, "--notes", body)
        return
    release, extras = mine[0], mine[1:]
    if release["tag_name"] != tag:
        old_tag = release["tag_name"]
        branch = api(API)["default_branch"]  # type: ignore[index]
        api("-X", "PATCH", f"{API}/releases/{release['id']}", "-f", f"tag_name={tag}",
            "-f", f"target_commitish={branch}")
        delete_tag(old_tag)
    api("-X", "PATCH", f"{API}/releases/{release['id']}", "-f", f"name={release_title}", "-f", f"body={body}")

    release = api(f"{API}/releases/{release['id']}")  # type: ignore[assignment]
    same = next((a for a in release["assets"] if a["name"] == apk.name), None)
    if not (same and same.get("digest") == f"sha256:{sha256(apk)}"):
        gh("release", "upload", tag, str(apk), "--clobber")
        release = api(f"{API}/releases/{release['id']}")  # type: ignore[assignment]
    if apk.name not in {a["name"] for a in release["assets"]}:
        raise SystemExit(f"{apk.name} is not on release {tag} after upload")
    for asset in release["assets"]:
        if asset["name"] != apk.name:
            delete_asset(asset)
    for extra in extras:
        delete_release(extra)


def publish_state(state: Path, dry: bool) -> None:
    print(f"{STATE_TAG}: patch state  <-  {state}")
    if dry:
        return
    body = "Internal: saved patch state of the local runner. Not an app release."
    release = next((r for r in list_releases() if r["tag_name"] == STATE_TAG), None)
    if release is None:
        gh("release", "create", STATE_TAG, str(state), "--title", "Patch state", "--notes", body, "--prerelease")
    else:
        gh("release", "upload", STATE_TAG, str(state), "--clobber")
        api("-X", "PATCH", f"{API}/releases/{release['id']}", "-f", "name=Patch state",
            "-f", f"body={body}", "-F", "prerelease=true")


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
