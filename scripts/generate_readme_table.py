#!/usr/bin/env python3
"""Regenerate the README "Available builds" table.

The table is built from ``patch-config.json`` (which apps, sorted by display name), the
``sources/*.json`` files (patch repository and display name) and the assets on
the GitHub release (which architecture is actually published). Each row gets an
Obtainium import link that offers only that app's APK from the release (an APK
filter, because all builds share one release) with version detection off and no
pseudo-version, so Obtainium just offers the APK on the release.

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

It also writes docs/index.html, a small GitHub Pages page that forwards to one
obtainium://apps/ link importing every published app. Obtainium's own redirect
page rejects the bulk form, and GitHub strips custom-scheme links from the README,
so the README links to this page instead (enable Pages for the /docs folder).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
START, END = "<!-- available-builds:start -->", "<!-- available-builds:end -->"
PAGE = ROOT / "docs" / "index.html"
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


def obtainium_payload(repo_url: str, owner: str, app: str, name: str, package: str) -> dict:
    # Only this app's APK from the shared release. Every build is published under the
    # same "latest" tag, so there is no version number to compare: version detection is
    # off and no pseudo-version (release date or title) is used. Obtainium simply offers
    # whatever APK is on the release.
    settings = json.dumps(
        {"apkFilterRegEx": f"^{re.escape(app)}-", "versionDetection": False},
        separators=(",", ":"),
    )
    return {"id": package, "url": repo_url, "author": owner, "name": name, "additionalSettings": settings}


def obtainium_link(payload: dict) -> str:
    """One-app import link through Obtainium's redirect page (it only accepts obtainium://app/)."""
    inner = quote(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), safe="")
    return "https://apps.obtainium.imranr.dev/redirect?r=" + quote("obtainium://app/" + inner, safe="")


def bulk_deep_link(payloads: list[dict]) -> str:
    inner = quote(json.dumps(payloads, separators=(",", ":"), ensure_ascii=False), safe="")
    return "obtainium://apps/" + inner


def render_page(payloads: list[dict]) -> str:
    """The GitHub Pages page: opens Obtainium with every app, with a manual button."""
    deep = html.escape(bulk_deep_link(payloads), quote=True)
    items = "\n".join(f"      <li>{html.escape(p['name'])}</li>" for p in payloads)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Add all apps to Obtainium</title>
  <style>
    body {{ font: 16px/1.5 system-ui, sans-serif; max-width: 34rem; margin: 3rem auto; padding: 0 1rem; }}
    a.button {{ display: inline-block; padding: .7rem 1.2rem; border-radius: .6rem; background: #5b4bd5; color: #fff; text-decoration: none; }}
    small {{ color: #666; }}
  </style>
</head>
<body>
  <h1>Add all apps to Obtainium</h1>
  <p>This opens Obtainium with {len(payloads)} apps from this repository's release. Obtainium asks you to confirm before it adds anything.</p>
  <p><a class="button" id="open" href="{deep}">Open Obtainium</a></p>
  <p><small>Nothing happened? Install <a href="https://github.com/ImranR98/Obtainium/releases/latest">Obtainium</a> first, then tap the button again.</small></p>
  <ul>
{items}
  </ul>
  <script>setTimeout(function () {{ location.href = document.getElementById("open").href; }}, 800);</script>
</body>
</html>
"""


def build_table(tag: str) -> tuple[str, list[dict], str]:
    """Return the table markdown, the Obtainium payloads of the published apps and the repo URL."""
    config = json.loads((ROOT / "patch-config.json").read_text())["patch_list"]
    release = gh_json(f"repos/{{owner}}/{{repo}}/releases/tags/{tag}")
    repo_url = re.sub(r"/releases/.*$", "", release["html_url"])
    owner = repo_url.rstrip("/").split("/")[-2]
    published: dict[str, str] = {}
    for asset in release.get("assets", []):
        match = ASSET.match(asset["name"])
        if match and asset["name"].endswith(".apk"):
            published[match["app"]] = match["arch"]

    payloads: list[dict] = []
    rows = ["| App | Patches | Architecture | Obtainium |", "| --- | --- | --- | --- |"]
    # Alphabetical by display name, whatever the build order in patch-config.json.
    for entry in sorted(config, key=lambda e: (e.get("title") or e["app_name"]).casefold()):
        app, source = entry["app_name"], entry["source"]
        title = entry.get("title") or app
        source_title, patch_repo = source_info(source)
        patches = f"[{source_title}](https://github.com/{patch_repo})" if patch_repo else source_title
        package = entry.get("package") or store_package(app)
        if app not in published or not package:
            reason = "not published yet" if app not in published else "no package id"
            rows.append(f"| {title} | {patches} | {reason} | |")
            continue
        payload = obtainium_payload(repo_url, owner, app, f"{title} ({source_title})", package)
        payloads.append(payload)
        link = obtainium_link(payload)
        rows.append(f"| {title} | {patches} | {published[app]} | [Add to Obtainium]({link}) |")
    return "\n".join(rows) + "\n", payloads, repo_url


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
    table, payloads, repo_url = build_table(args.tag)
    owner, repo = repo_url.rstrip("/").split("/")[-2:]
    pages_url = f"https://{owner}.github.io/{repo}/"
    bulk = f"\n[Add all {len(payloads)} apps to Obtainium at once]({pages_url})\n" if payloads else ""
    updated = f"{head}{START}\n{table}{bulk}{END}{tail}"
    page = render_page(payloads)

    current_page = PAGE.read_text() if PAGE.exists() else None
    if updated == readme and page == current_page:
        print("README.md and docs/index.html are up to date.")
        return 0
    if args.check:
        print("README.md table or docs/index.html is out of date; run scripts/generate_readme_table.py", file=sys.stderr)
        return 1
    readme_path.write_text(updated)
    PAGE.parent.mkdir(exist_ok=True)
    PAGE.write_text(page)
    print("README.md and docs/index.html updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
