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
_FILTERING = re.compile(r"^INFO: Filtering patches for (\S+) v(\S+)")


def parse(output: str | None, rules: list[str] | None = None) -> dict:
    """Turn the CLI's patch output into a report (``rules`` are the custom -e/-d arguments)."""
    report: dict = {"applied": [], "disabled": [], "incompatible": [], "failed": [], "rules": rules or []}
    for line in (output or "").splitlines():
        if match := _FILTERING.match(line):
            report["package"], report["app_version"] = match.group(1), match.group(2)
        elif match := _APPLIED.match(line):
            report["applied"].append(match.group(1))
        elif match := _DISABLED.match(line):
            report["disabled"].append({"name": match.group(1), "why": match.group(2) or ""})
        elif match := _INCOMPATIBLE.match(line):
            report["incompatible"].append({"name": match.group(1), "why": match.group(2)})
        elif match := _FAILED.match(line):
            report["failed"].append(match.group(1))
    return report


def describe(cli: Path | str, patches: Path | str, package: str) -> dict[str, dict]:
    """What each patch of a bundle does for one app: {name: {"description", "default_on"}}."""
    from src import utils

    out = utils.run_process(
        ["java", "-jar", str(cli), "list-patches", "-f", package, "--patches", str(patches)],
        capture=True, silent=True, check=False,
    ) or ""
    info: dict[str, dict] = {}
    for block in out.split("Index:"):
        lines = block.splitlines()
        name = next((l.split("Name:", 1)[1].strip() for l in lines if l.startswith("Name:")), None)
        if not name:
            continue
        info[name] = {
            "description": next((l.split("Description:", 1)[1].strip() for l in lines if l.startswith("Description:")), ""),
            "default_on": "Enabled: true" in block,
        }
    return info


def enrich(report: dict, info: dict[str, dict], bundle: str = "", cli: str = "") -> dict:
    """Attach each patch's description (and the bundle used) to a report."""
    report["applied"] = [
        {"name": a, "description": info.get(a, {}).get("description", "")} if isinstance(a, str) else a
        for a in report["applied"]
    ]
    for item in report["disabled"]:
        item.setdefault("description", info.get(item["name"], {}).get("description", ""))
    if bundle:
        report["bundle"] = bundle
    if cli:
        report["cli"] = cli
    return report


def infer(info: dict[str, dict], rules: list[str] | None = None) -> dict:
    """Report for a build made before reports existed: the bundle's defaults plus the list's rules."""
    enabled = {name for name, v in info.items() if v["default_on"]}
    for rule in rules or []:
        name = rule[1:].strip().split("{")[0].strip()
        (enabled.add if rule.startswith("+") else enabled.discard)(name)
    report = {
        "applied": [n for n in info if n in enabled],
        "disabled": [{"name": n, "why": "default"} for n in info if n not in enabled],
        "incompatible": [], "failed": [], "rules": rules or [], "inferred": True,
    }
    return report


def report_path(apk: Path) -> Path:
    return apk.with_suffix(".patches.json")


def save(apk: Path, report: dict) -> Path:
    path = report_path(apk)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return path


def _name(item) -> str:
    return item if isinstance(item, str) else item["name"]


def summary(report: dict) -> str:
    parts = [f"{len(report['applied'])} applied", f"{len(report['disabled'])} off"]
    if report["incompatible"]:
        parts.append(f"{len(report['incompatible'])} incompatible")
    if report["failed"]:
        parts.append(f"{len(report['failed'])} failed")
    return ", ".join(parts)


def markdown(report: dict) -> str:
    """Release-notes section explaining what is patched: every applied patch with what it does."""
    def entry(item, limit: int | None = None) -> str:
        name = _name(item)
        desc = "" if isinstance(item, str) else item.get("description", "")
        if limit and len(desc) > limit:
            desc = desc[:limit].rsplit(" ", 1)[0] + "…"
        return f"- **{name}**" + (f": {desc}" if desc else "")

    head = "### What is patched\n"
    bundle = report.get("bundle")
    head += (f"Patched with `{bundle}`" + (f" ({report['cli']})" if report.get("cli") else "") + ". ") if bundle else ""
    head += ("Patches are changes made to the app when it is built; a patch that is off is not in this APK at all. "
             "Many patches add a switch in the app's own settings.")
    if report.get("inferred"):
        head += "\n\n_This build predates the patch report; the lists below are what the patch bundle enables by default plus the custom rules, not read from the build log._"
    lines = [head, "", f"### Patches applied ({len(report['applied'])})"]
    lines += [entry(a) for a in report["applied"]] or ["- none"]
    off = report["disabled"]
    lines += ["", f"### Patches off ({len(off)})"]
    lines += [entry(d, 140) + (f" _({'off by default' if d['why'] == 'default' else d['why']})_" if d.get("why") else "") for d in off] or ["- none"]
    if report["incompatible"]:
        lines += ["", f"### Skipped as incompatible ({len(report['incompatible'])})"]
        lines += [f"- **{d['name']}**: {d['why']}" for d in report["incompatible"]]
    if report["failed"]:
        lines += ["", f"### Failed ({len(report['failed'])})"] + [f"- {n}" for n in report["failed"]]
    if report["rules"]:
        lines += ["", "### Custom rules", *[f"- `{r}`" for r in report["rules"]]]
    return "\n".join(lines).rstrip() + "\n"
