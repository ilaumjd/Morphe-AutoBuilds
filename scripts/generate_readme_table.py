#!/usr/bin/env python3
"""Regenerate the README "Available builds" table.

The table is built from ``patch-config.json`` (which apps, sorted by display name), the
``sources/*.json`` files (patch repository and display name) and the assets on
the per-app GitHub releases (which architecture and version are published). Each row gets an
Obtainium import link: it selects the app's own release by title, takes the
release title ("<App> <version>") as the version and cuts the version number off
its end, so Obtainium compares real versions.

Optional metadata:
  patch-config.json entry   "title"    display name (default: the app name)
                            "package"  package id of the *patched* APK, when it
                                       differs from the store package id
  sources/<source>.json     "title" in the first entry: display name of the
                            patch source (default: its name)

The table is written between the ``<!-- available-builds:start -->`` and
``<!-- available-builds:end -->`` markers in README.md. Use ``--check`` to fail
when the README is out of date instead of writing it. Needs the ``gh`` CLI and
runs from a checkout of the repository.

It also writes obtainium-apps.json, an import file with every published app (the same
objects as the per-app links) for Obtainium's Import screen. Obtainium's redirect page
rejects the bulk obtainium://apps/ form and GitHub strips custom-scheme links, so a
file is the way to add all apps at once.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
START, END = "<!-- available-builds:start -->", "<!-- available-builds:end -->"
IMPORT_FILE = ROOT / "obtainium-apps.json"
ASSET = re.compile(
    r"^(?P<app>[^-]+)-(?P<arch>arm64-v8a|armeabi-v7a|universal)-(?P<source>[^-]+)"
    r"-v(?P<version>.+)-(?P<date>\d{8})\.apk$"
)


def gh_json(path: str) -> dict:
    out = subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def store_package(app: str) -> str | None:
    """Package id from the first store config that has one."""
    for config in sorted((ROOT / "apps").glob(f"*/{app}.json")):
        package = json.loads(config.read_text()).get("package")
        if package:
            return package
    return None


def source_info(source: str) -> tuple[str, str | None]:
    """Display name and ``owner/repo`` of the patch bundle for a source."""
    entries = json.loads((ROOT / "sources" / f"{source}.json").read_text())
    title = entries[0].get("title") or entries[0]["name"]
    repo = next(
        (f"{e['user']}/{e['repo']}" for e in entries[1:] if e.get("repo") != "morphe-cli"), None
    )
    return title, repo


def obtainium_payload(repo_url: str, owner: str, app: str, title: str, name: str, package: str) -> dict:
    # Every app has its own release (tag = app name) titled "<title> <version>", so
    # Obtainium picks the app's release by title, takes the release title as the version
    # and cuts the version number off its end: a real version that it can compare with
    # the installed one (no pseudo-version, version detection left at its default).
    title_pattern = re.escape(title).replace("\\ ", " ")
    settings = json.dumps(
        {
            "apkFilterRegEx": f"^{re.escape(app)}-",
            "filterReleaseTitlesByRegEx": f"^{title_pattern} ",
            "releaseTitleAsVersion": True,
            "versionExtractionRegEx": r"(\S+)$",
            "matchGroupToUse": "$1",
        },
        separators=(",", ":"),
    )
    return {"id": package, "url": repo_url, "author": owner, "name": name, "additionalSettings": settings}


def obtainium_link(payload: dict) -> str:
    """One-app import link through Obtainium's redirect page (it only accepts obtainium://app/)."""
    inner = quote(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), safe="")
    return "https://apps.obtainium.imranr.dev/redirect?r=" + quote("obtainium://app/" + inner, safe="")


def import_file_json(payloads: list[dict]) -> str:
    """Obtainium import file: {"apps": [...]}, the same app objects as the per-app links.

    Obtainium's Import accepts this wrapper (it needs no schema version or settings)."""
    return json.dumps({"apps": payloads}, indent=2, ensure_ascii=False) + "\n"


def build_table() -> tuple[str, list[dict], str]:
    """Return the table markdown, the Obtainium payloads of the published apps and the repo URL."""
    config = json.loads((ROOT / "patch-config.json").read_text())["patch_list"]
    repo_url = gh_json("repos/{owner}/{repo}")["html_url"]
    owner = repo_url.rstrip("/").split("/")[-2]
    # Each app has its own release; find the APK each one publishes.
    published: dict[str, tuple[str, str, str]] = {}  # app -> (arch, version, release page)
    for release in gh_json("repos/{owner}/{repo}/releases?per_page=100"):
        for asset in release.get("assets", []):
            match = ASSET.match(asset["name"])
            if match and asset["name"].endswith(".apk"):
                published[match["app"]] = (match["arch"], match["version"], release["html_url"])

    payloads: list[dict] = []
    rows = ["| App | Patches | Architecture | Release | Obtainium |", "| --- | --- | --- | --- | --- |"]
    # Alphabetical by display name, whatever the build order in patch-config.json.
    for entry in sorted(config, key=lambda e: (e.get("title") or e["app_name"]).casefold()):
        app, source = entry["app_name"], entry["source"]
        title = entry.get("title") or app
        source_title, patch_repo = source_info(source)
        patches = f"[{source_title}](https://github.com/{patch_repo})" if patch_repo else source_title
        package = entry.get("package") or store_package(app)
        if app not in published or not package:
            reason = "not published yet" if app not in published else "no package id"
            rows.append(f"| {title} | {patches} | {reason} | | |")
            continue
        arch, version, release_url = published[app]
        payload = obtainium_payload(repo_url, owner, app, title, f"{title} ({source_title})", package)
        payloads.append(payload)
        link = obtainium_link(payload)
        rows.append(f"| {title} | {patches} | {arch} | [{version}]({release_url}) | [Add to Obtainium]({link}) |")
    return "\n".join(rows) + "\n", payloads, repo_url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if README.md is out of date")
    args = parser.parse_args()

    readme_path = ROOT / "README.md"
    readme = readme_path.read_text()
    if START not in readme or END not in readme:
        print(f"README.md needs the {START} and {END} markers around the table.", file=sys.stderr)
        return 2
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    table, payloads, repo_url = build_table()
    owner, repo = repo_url.rstrip("/").split("/")[-2:]
    file_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{IMPORT_FILE.name}"
    bulk = (
        f"\nAll {len(payloads)} apps at once: download [{IMPORT_FILE.name}]({file_url}) and import it in "
        "Obtainium (Import/Export → Import).\n"
        if payloads else ""
    )
    updated = f"{head}{START}\n{table}{bulk}{END}{tail}"
    import_file = import_file_json(payloads)

    current_file = IMPORT_FILE.read_text() if IMPORT_FILE.exists() else None
    if updated == readme and import_file == current_file:
        print("README.md and obtainium-apps.json are up to date.")
        return 0
    if args.check:
        print("README.md table or obtainium-apps.json is out of date; run scripts/generate_readme_table.py", file=sys.stderr)
        return 1
    readme_path.write_text(updated)
    IMPORT_FILE.write_text(import_file)
    print("README.md and obtainium-apps.json updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
