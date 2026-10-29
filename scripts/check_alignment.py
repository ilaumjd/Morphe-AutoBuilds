#!/usr/bin/env python3
"""Mark each patched APK as aligned (✅) or misaligned (❌).

Android needs stored native libraries (.so) on 4096-byte boundaries and resources.arsc on 4
bytes. A misaligned APK can fail to open. Usage: python scripts/check_alignment.py [APK ...]
(default: every APK in apks/patched). Exit status 1 if any APK is misaligned.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import manifest  # noqa: E402


def main() -> int:
    apks = [Path(a) for a in sys.argv[1:]] or sorted(Path("apks/patched").glob("*.apk"))
    bad_count = 0
    for apk in apks:
        bad = manifest._misaligned(apk)
        mark = "\u274c" if bad else "\u2705"
        detail = f"  ({len(bad)} misaligned, e.g. {sorted(bad)[0]})" if bad else ""
        print(f"{mark} {apk.name}{detail}")
        bad_count += bool(bad)
    print(f"{len(apks) - bad_count} aligned, {bad_count} misaligned")
    return 1 if bad_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
