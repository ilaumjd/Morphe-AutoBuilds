#!/usr/bin/env python3
"""Give every patched APK in apks/patched a patch report with descriptions.

Builds made after patch reports existed already have <apk>.patches.json; this adds each
patch's description (and the bundle used). Older builds get a report inferred from the
patch bundle's defaults plus the app's patches/<app>-<source>.txt rules, marked as
inferred. Needs Java and network access to fetch the current patch bundles; run it from
the repository root (it is meant for the builder container):

    python scripts/backfill_patch_reports.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from src import downloader, patchlog  # noqa: E402
from src.__main__ import find_tools, patch_rule_lines  # noqa: E402
from src.paths import PATCHED_APKS_DIR  # noqa: E402

ASSET = re.compile(
    r"^(?P<app>[^-]+)-(?P<arch>arm64-v8a|armeabi-v7a|universal)-(?P<source>[^-]+)-v(?P<version>.+)-(?P<date>\d{8})\.apk$"
)


def store_package(app: str) -> str | None:
    for config in sorted((ROOT / "apps").glob(f"*/{app}.json")):
        package = json.loads(config.read_text()).get("package")
        if package:
            return package
    return None


def main() -> int:
    work = Path("/tmp/backfill")
    tools: dict[str, tuple[Path, Path]] = {}
    for apk in sorted(PATCHED_APKS_DIR.glob("*.apk")):
        match = ASSET.match(apk.name)
        if not match:
            continue
        app, source = match["app"], match["source"]
        if source not in tools:
            folder = work / source
            folder.mkdir(parents=True, exist_ok=True)
            os.chdir(folder)
            (folder / "sources").unlink(missing_ok=True)
            (folder / "sources").symlink_to(ROOT / "sources")
            files, _ = downloader.download_required(source)
            tools[source] = find_tools(files)
            tools[source] = (folder / tools[source][0].name, folder / tools[source][1].name)
            os.chdir(ROOT)
        cli, bundle = tools[source]
        path = patchlog.report_path(apk)
        existing = json.loads(path.read_text()) if path.exists() else None
        package = (existing or {}).get("package") or store_package(app)
        info = patchlog.describe(cli, bundle, package)
        report = existing or patchlog.infer(info, patch_rule_lines(app, source))
        report.setdefault("package", package)
        patchlog.enrich(report, info, bundle.name, cli.name)
        patchlog.save(apk, report)
        print(f"{apk.name}: {patchlog.summary(report)}{' (inferred)' if report.get('inferred') else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
