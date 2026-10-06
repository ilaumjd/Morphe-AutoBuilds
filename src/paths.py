"""Where the pipeline keeps APKs.

Everything lives under ``apks/`` (relative to the working directory):

    apks/original/   stock APKs (.apk, .apks, .apkm, .xapk) as downloaded
    apks/patched/    signed, patched builds

Neither folder is ever cleaned by the pipeline. Override the locations with
APKS_DIR, ORIGINAL_APKS_DIR or PATCHED_APKS_DIR.
"""
from os import getenv
from pathlib import Path

APKS_DIR = Path(getenv("APKS_DIR", "apks"))
ORIGINAL_APKS_DIR = Path(getenv("ORIGINAL_APKS_DIR") or APKS_DIR / "original")
PATCHED_APKS_DIR = Path(getenv("PATCHED_APKS_DIR") or APKS_DIR / "patched")
