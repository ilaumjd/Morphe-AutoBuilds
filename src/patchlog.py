"""Record which patches a build applied, skipped or switched off.

The Morphe CLI reports every patch while patching ("Applied: ...", "Skipping disabled: ...",
'Skipping "...": incompatible ...', "FAILED: ..."). The build parses that output into a
small report stored next to the patched APK (``<apk>.patches.json``); the release notes
and the console summary are built from it, so each build can be reviewed afterwards.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_APPLIED = re.compile(r"^INFO: Applied: (.+?)\s*$")
_DISABLED = re.compile(r"^INFO: Skipping disabled: (.+?)(?: \(([^)]*)\))?\s*$")
_INCOMPATIBLE = re.compile(r'^WARNING: Skipping "(.+?)": (.+?)\s*$')
_FAILED = re.compile(r"^SEVERE: FAILED: (.+?)\s*$")


def parse(output: str | None, rules: list[str] | None = None) -> dict:
    """Turn the CLI's patch output into a report (``rules`` are the custom -e/-d arguments)."""
    report: dict = {"applied": [], "disabled": [], "incompatible": [], "failed": [], "rules": rules or []}
    for line in (output or "").splitlines():
        if match := _APPLIED.match(line):
            report["applied"].append(match.group(1))
        elif match := _DISABLED.match(line):
            report["disabled"].append({"name": match.group(1), "why": match.group(2) or ""})
        elif match := _INCOMPATIBLE.match(line):
            report["incompatible"].append({"name": match.group(1), "why": match.group(2)})
        elif match := _FAILED.match(line):
            report["failed"].append(match.group(1))
    return report


def report_path(apk: Path) -> Path:
    return apk.with_suffix(".patches.json")


def save(apk: Path, report: dict) -> Path:
    path = report_path(apk)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return path


def summary(report: dict) -> str:
    parts = [f"{len(report['applied'])} applied", f"{len(report['disabled'])} off"]
    if report["incompatible"]:
        parts.append(f"{len(report['incompatible'])} incompatible")
    if report["failed"]:
        parts.append(f"{len(report['failed'])} failed")
    return ", ".join(parts)


def markdown(report: dict) -> str:
    """Release-notes section listing what was applied and what was left off."""
    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) or "- none"

    lines = [f"### Patches applied ({len(report['applied'])})", bullets(report["applied"]), ""]
    off = [f"{d['name']} ({d['why']})" if d["why"] else d["name"] for d in report["disabled"]]
    lines += [f"### Patches off ({len(off)})", bullets(off), ""]
    if report["incompatible"]:
        lines += [f"### Skipped as incompatible ({len(report['incompatible'])})",
                  bullets([f"{d['name']}: {d['why']}" for d in report["incompatible"]]), ""]
    if report["rules"]:
        lines += ["### Custom rules", bullets(report["rules"]), ""]
    return "\n".join(lines).rstrip() + "\n"
