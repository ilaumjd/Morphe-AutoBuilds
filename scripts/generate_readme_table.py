#!/usr/bin/env python3
"""Regenerate the README "Available builds" table.

The table is built from ``patch-config.json`` (which apps, in that order), the
``sources/*.json`` files (patch repository and display name) and the assets on
the GitHub release (which architecture is actually published). Each row gets an
Obtainium import link that offers only that app's APK from the release (an APK
filter, because all builds share one release) with version detection turned off.

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
ASSET = re.compile(r"^(?P<app>[^-]+)-(?P<arch>arm64-v8a|armeabi-v7a|universal)-")


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


def obtainium_link(repo_url: str, owner: str, app: str, name: str, package: str) -> str:
    # Only this app's APK from the shared release, and no version handling: every
    # build is published under the same "latest" tag, so Obtainium must not compare
    # versions (no version detection, no release-date or release-title versions).
    settings = json.dumps(
        {"apkFilterRegEx": f"^{re.escape(app)}-", "versionDetection": False}, separators=(",", ":")
    )
    payload = {"id": package, "url": repo_url, "author": owner, "name": name, "additionalSettings": settings}
    inner = quote(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), safe="")
    return "https://apps.obtainium.imranr.dev/redirect?r=" + quote("obtainium://app/" + inner, safe="")


def build_table(tag: str) -> str:
    config = json.loads((ROOT / "patch-config.json").read_text())["patch_list"]
    release = gh_json(f"repos/{{owner}}/{{repo}}/releases/tags/{tag}")
    repo_url = re.sub(r"/releases/.*$", "", release["html_url"])
    owner = repo_url.rstrip("/").split("/")[-2]
    published: dict[str, str] = {}
    for asset in release.get("assets", []):
        match = ASSET.match(asset["name"])
        if match and asset["name"].endswith(".apk"):
            published[match["app"]] = match["arch"]

    rows = ["| App | Patches | Architecture | Obtainium |", "| --- | --- | --- | --- |"]
    for entry in config:
        app, source = entry["app_name"], entry["source"]
        title = entry.get("title") or app
        source_title, patch_repo = source_info(source)
        patches = f"[{source_title}](https://github.com/{patch_repo})" if patch_repo else source_title
        package = entry.get("package") or store_package(app)
        if app not in published or not package:
            reason = "not published yet" if app not in published else "no package id"
            rows.append(f"| {title} | {patches} | {reason} | |")
            continue
        link = obtainium_link(repo_url, owner, app, f"{title} ({source_title})", package)
        rows.append(f"| {title} | {patches} | {published[app]} | [Add to Obtainium]({link}) |")
    return "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default="latest", help="release tag to read (default: latest)")
    parser.add_argument("--check", action="store_true", help="exit 1 if README.md is out of date")
    args = parser.parse_args()

    readme_path = ROOT / "README.md"
    readme = readme_path.read_text()
    if START not in readme or END not in readme:
        print(f"README.md needs the {START} and {END} markers around the table.", file=sys.stderr)
        return 2
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    updated = f"{head}{START}\n{build_table(args.tag)}{END}{tail}"

    if updated == readme:
        print("README.md is up to date.")
        return 0
    if args.check:
        print("README.md Available builds table is out of date; run scripts/generate_readme_table.py", file=sys.stderr)
        return 1
    readme_path.write_text(updated)
    print("README.md updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
