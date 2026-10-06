"""Where the pipeline keeps APKs, and how they are named.

Everything lives under ``apks/`` (relative to the working directory):

    apks/original/   <app>-<arch>-original-v<version>.<ext>
    apks/patched/    <app>-<arch>-<source>-v<version>-<UTC date>.apk

Originals keep the store's format (.apk, .apks, .apkm or .xapk). The pipeline
finds an original purely by this name, so a file placed here by hand with the
right name is picked up as-is. Neither folder is ever cleaned by the pipeline.
Override the locations with APKS_DIR, ORIGINAL_APKS_DIR or PATCHED_APKS_DIR.
"""
import re
from os import getenv
from pathlib import Path

APKS_DIR = Path(getenv("APKS_DIR", "apks"))
ORIGINAL_APKS_DIR = Path(getenv("ORIGINAL_APKS_DIR") or APKS_DIR / "original")
PATCHED_APKS_DIR = Path(getenv("PATCHED_APKS_DIR") or APKS_DIR / "patched")

ORIGINAL_SUFFIXES = (".apk", ".apks", ".apkm", ".xapk")


def _safe(part: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", part)


def original_stem(app_name: str, arch: str, version: str) -> str:
    """File name (without extension) of a stored original APK."""
    return f"{_safe(app_name)}-{_safe(arch)}-original-v{_safe(version)}"


def original_candidates(app_name: str, arch: str, version: str) -> list[Path]:
    """Every path an original for this app/arch/version may be stored at."""
    stem = original_stem(app_name, arch, version)
    return [ORIGINAL_APKS_DIR / f"{stem}{suffix}" for suffix in ORIGINAL_SUFFIXES]


def patched_apk(app_name: str, arch: str, source: str, version: str, build_date: str) -> Path:
    """Path of a signed patched build."""
    return PATCHED_APKS_DIR / f"{app_name}-{arch}-{source}-v{version}-{build_date}.apk"
