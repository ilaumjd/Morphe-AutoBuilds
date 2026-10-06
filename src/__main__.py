import json
import logging
import re
import os
import zipfile
from datetime import datetime, timezone
from sys import exit
from pathlib import Path
from os import getenv
import subprocess
import sys
from src import (
    utils,
    downloader
)
from src.paths import PATCHED_APKS_DIR

KEYSTORE = {
    "path": getenv("KEYSTORE_PATH", "keystore/public.jks"),
    "password": getenv("KEYSTORE_PASSWORD", "public"),
    "alias": getenv("KEYSTORE_ALIAS", "public"),
}
BUILD_DATE = getenv("BUILD_DATE") or datetime.now(timezone.utc).strftime("%Y%m%d")

def _should_retry_with_older_version(output: str | None) -> bool:
    """Detect common patterns that indicate the chosen app version is not
    actually compatible with the selected patches (fingerprint mismatch, etc.)."""
    if not output:
        return False
    t = output.lower()
    return (
        "failed to match the fingerprint" in t
        or "patch.patchexception" in t
        or ("fingerprint" in t and "failed" in t)
        or "patching aborted" in t
    )

def load_patch_rules(app_name: str, source: str) -> list[str]:
    """Translate patches/<app>-<source>.txt into Morphe CLI arguments.

    ``- Patch name`` disables a patch. ``+ Patch name {key=value, ...}``
    enables a patch and sets its options.
    """
    args: list[str] = []
    patches_path = Path("patches") / f"{app_name}-{source}.txt"
    if not patches_path.exists():
        return args

    for line in patches_path.read_text().splitlines():
        line = line.strip()
        if line.startswith('-'):
            args.extend(["-d", line[1:].strip()])
        elif line.startswith('+'):
            name_opts = line[1:].strip()
            opts: list[str] = []
            if "{" in name_opts and name_opts.endswith("}"):
                name_part, opts_part = name_opts.split("{", 1)
                name_opts = name_part.strip()
                for opt in opts_part.rstrip("}").split(","):
                    opt = opt.strip()
                    if opt:
                        opts.append(f"-O{opt}")
            args.extend(["-e", name_opts, *opts])
    return args

def find_tools(download_files: list[Path]) -> tuple[Path | None, Path | None]:
    """Pick the Morphe CLI jar and patch bundle from the downloaded files."""
    cli = utils.find_file(download_files, ".jar", contains="morphe")
    patches = utils.find_file(download_files, ".mpp")
    return cli, patches

def normalize_input(input_apk: Path) -> Path:
    """Turn a downloaded .apk/.apkm/.xapk/.apks into a single .apk file."""
    if input_apk.suffix == ".apk":
        return input_apk

    # Split bundles contain the base and config splits as nested .apk files.
    is_bundle = False
    try:
        if zipfile.is_zipfile(input_apk):
            with zipfile.ZipFile(input_apk, "r") as z:
                is_bundle = (
                    any(n.endswith(".apk") for n in z.namelist())
                    or input_apk.suffix.lower() in [".apkm", ".xapk", ".apks", ".zip"]
                )
    except Exception as e:
        logging.debug(f"Zip inspection failed for {input_apk}: {e}")

    target_apk = input_apk.with_suffix(".apk")
    target_apk.unlink(missing_ok=True)

    if is_bundle:
        logging.info(f"Input file is a bundle ({input_apk.name}), using APKEditor to merge")
        apk_editor = downloader.download_apkeditor()
        try:
            utils.run_process([
                "java", "-jar", str(apk_editor), "m",
                "-f",
                "-i", str(input_apk),
                "-o", str(target_apk)
            ], silent=True)
            input_apk.unlink(missing_ok=True)
            input_apk = target_apk
        except Exception as e:
            logging.warning(f"APKEditor merge failed ({e}); trying file as a standalone APK")
            os.replace(input_apk, target_apk)
            input_apk = target_apk
    else:
        logging.info(f"Normalizing standalone APK filename to {target_apk.name}")
        os.replace(input_apk, target_apk)
        input_apk = target_apk

    # Remove build numbers like (1575420) and -1575420_. Only strip 6+ digit
    # tokens so legitimate short version segments (e.g. "app-2_0") survive.
    clean_name = re.sub(r'\(\d+\)', '', input_apk.name)
    clean_name = re.sub(r'-\d{6,}_', '_', clean_name)
    if clean_name != input_apk.name:
        clean_apk = input_apk.with_name(clean_name)
        clean_apk.unlink(missing_ok=True)
        os.replace(input_apk, clean_apk)
        input_apk = clean_apk

    logging.info(f"Normalized APK file: {input_apk}")
    return input_apk

def strip_native_libs(input_apk: Path, arch: str) -> None:
    """Drop native libraries the target architecture doesn't need."""
    patterns = ["lib/x86/*", "lib/x86_64/*"]
    if arch == "arm64-v8a":
        patterns.append("lib/armeabi-v7a/*")
    elif arch == "armeabi-v7a":
        patterns.append("lib/arm64-v8a/*")
    logging.info(f"Stripping native libraries for {arch}...")
    utils.strip_zip_entries(input_apk, patterns)

def sign_apk(unsigned_apk: Path, signed_apk: Path) -> None:
    apksigner = utils.find_apksigner()
    if not apksigner:
        raise RuntimeError("apksigner not found")

    utils.run_process([
        str(apksigner), "sign",
        "--ks", KEYSTORE["path"],
        "--ks-pass", f"pass:{KEYSTORE['password']}",
        "--key-pass", f"pass:{KEYSTORE['password']}",
        "--ks-key-alias", KEYSTORE["alias"],
        "--in", str(unsigned_apk), "--out", str(signed_apk)
    ])

def download_apk(app_name: str, cli: Path, patches: Path, arch: str, cached_only: bool = False):
    """Return a usable original APK, optionally using the local cache only."""
    for platform in downloader.PLATFORMS:
        apk_path, ver, cands = downloader.download_platform(
            app_name, platform, str(cli), str(patches), arch, cached_only=cached_only
        )
        if not apk_path:
            continue
        # A corrupt download must never reach the patcher: repair it, and if
        # it is still unusable, discard it and try the next store.
        apk_path = utils.ensure_usable_apk(apk_path, app_name, ver or "")
        if apk_path is None:
            logging.warning(f"Discarding unusable download from {platform}; trying next store")
            continue
        return apk_path, ver, cands, platform
    return None, None, [], None

def download_original(app_name: str, cli: Path, patches: Path, arch: str) -> bool:
    """Fetch and validate an original APK, leaving its persistent cache intact."""
    input_apk, version, _, _ = download_apk(app_name, cli, patches, arch)
    if input_apk is None or not version:
        return False
    input_apk.unlink(missing_ok=True)
    logging.info(f"✅ Original APK cached: {app_name} v{version} ({arch})")
    return True


def run_build(
    app_name: str, source: str, arch: str, cli: Path, patches: Path, name: str,
    cached_only: bool = False,
) -> str | None:
    """Patch and sign one app. The patch stage can be restricted to cached originals."""
    input_apk, version, candidates, platform = download_apk(
        app_name, cli, patches, arch, cached_only=cached_only
    )
    if input_apk is None or not version:
        location = "cache" if cached_only else "stores"
        logging.error(f"❌ Failed to obtain APK for {app_name} from {location}")
        return None

    # Try the downloaded version first, then older compatible versions from
    # the patch set, so one overstated compatibility entry can't break the build.
    versions_to_try: list[str] = [version]
    if candidates and version in candidates:
        versions_to_try += [v for v in candidates if v != version]

    patch_args = load_patch_rules(app_name, source)

    for attempt_idx, ver in enumerate(versions_to_try):
        if attempt_idx > 0:
            logging.warning(
                f"Retrying {app_name}/{source}/{arch} with older version {ver} due to patch failure..."
            )
            input_apk, _, _ = downloader.download_platform(
                app_name, platform, str(cli), str(patches), arch,
                override_version=ver, cached_only=cached_only,
            )
            if input_apk is None:
                continue
            input_apk = utils.ensure_usable_apk(input_apk, app_name, ver)
            if input_apk is None:
                logging.warning(f"Re-downloaded APK for {ver} is unusable; trying next version")
                continue
            version = ver

        input_apk = normalize_input(input_apk)
        strip_native_libs(input_apk, arch)

        # Safety net: bundle merging / lib stripping can corrupt the file.
        logging.info("Checking APK integrity...")
        input_apk = utils.ensure_usable_apk(input_apk, app_name, version)
        if input_apk is None:
            logging.error(f"APK for {app_name} v{version} is corrupt and could not be repaired; trying next version")
            continue

        output_apk = Path(f"{app_name}-{arch}-patch-v{version}.apk")

        try:
            utils.run_process([
                "java", "-jar", str(cli),
                "patch", "--patches", str(patches),
                "--out", str(output_apk), str(input_apk),
                *patch_args
            ], capture=True)
        except subprocess.CalledProcessError as e:
            # Remove temp files; we'll re-download if retrying.
            input_apk.unlink(missing_ok=True)
            output_apk.unlink(missing_ok=True)

            if attempt_idx < len(versions_to_try) - 1 and _should_retry_with_older_version(e.output):
                continue
            raise

        input_apk.unlink(missing_ok=True)

        signed_apk = PATCHED_APKS_DIR / f"{app_name}-{arch}-{name}-v{version}-{BUILD_DATE}.apk"
        signed_apk.parent.mkdir(parents=True, exist_ok=True)
        sign_apk(output_apk, signed_apk)
        output_apk.unlink(missing_ok=True)

        print(f"✅ APK built: {signed_apk.name}")
        return str(signed_apk)

    # Every candidate version failed.
    return None

def load_entries() -> list[dict]:
    """Return the build entries, optionally filtered by APP_NAME/SOURCE/ARCH."""
    with open("patch-config.json") as f:
        entries = json.load(f)["patch_list"]

    app_name, source, arch = getenv("APP_NAME"), getenv("SOURCE"), getenv("ARCH")
    if app_name:
        entries = [e for e in entries if e["app_name"] == app_name]
        if not entries:
            # Allow ad-hoc local builds of apps that aren't in the config yet.
            entries = [{"app_name": app_name, "source": source}]
    if source:
        entries = [e for e in entries if e["source"] == source]
    configured_sources = {
        item for item in getenv("SOURCES_TO_BUILD", "").split(",") if item
    }
    if configured_sources:
        entries = [entry for entry in entries if entry["source"] in configured_sources]
    if arch:
        entries = [{**e, "arches": [arch]} for e in entries]
    return entries

def main(stage: str = "all"):
    if stage not in {"all", "download", "patch"}:
        logging.error("Usage: python -m src [download|patch]")
        exit(2)
    entries = load_entries()
    if not entries or any(not e.get("source") for e in entries):
        logging.error("No matching entries in patch-config.json (set SOURCE for ad-hoc builds)")
        exit(1)

    tools: dict[str, tuple[Path, Path, str]] = {}
    built, failed = [], []
    source_results: dict[str, list[bool]] = {}

    for entry in entries:
        app_name, source = entry["app_name"], entry["source"]
        for arch in entry.get("arches") or ["universal"]:
            label = f"{app_name}/{source}/{arch}"
            action = "Downloading" if stage == "download" else "Patching"
            logging.info(f"🔨 {action} {label}...")
            try:
                if source not in tools:
                    download_files, name = downloader.download_required(source)
                    cli, patches = find_tools(download_files)
                    if not cli or not patches:
                        raise RuntimeError(
                            f"Morphe CLI or patches missing for {source}: {[f.name for f in download_files]}"
                        )
                    logging.info(f"✅ Using CLI: {cli.name}")
                    logging.info(f"✅ Using patches: {patches.name}")
                    tools[source] = (cli, patches, name)

                if stage == "download":
                    apk_path = download_original(app_name, *tools[source][:2], arch)
                else:
                    apk_path = run_build(
                        app_name, source, arch, *tools[source], cached_only=stage == "patch"
                    )
            except Exception as e:
                logging.error(f"❌ {label} failed: {e}")
                apk_path = None

            if not apk_path and arch == "arm64-v8a":
                fallback_label = f"{app_name}/{source}/universal"
                logging.warning(f"ARM64 {action.lower()} unavailable; retrying {fallback_label}...")
                try:
                    if stage == "download":
                        apk_path = download_original(app_name, *tools[source][:2], "universal")
                    else:
                        apk_path = run_build(
                            app_name, source, "universal", *tools[source], cached_only=stage == "patch"
                        )
                except Exception as e:
                    logging.error(f"❌ {fallback_label} failed: {e}")

            source_results.setdefault(source, []).append(bool(apk_path))
            result = label if stage == "download" else apk_path
            (built if apk_path else failed).append(result or label)

    successful_sources = [
        source for source, results in source_results.items() if all(results)
    ]
    Path(getenv("BUILD_RESULTS_PATH", "build-results.json")).write_text(
        json.dumps(
            {
                "built": built,
                "failed": failed,
                "successful_sources": successful_sources,
            },
            indent=2,
        )
        + "\n"
    )

    noun = "original APK(s)" if stage == "download" else "APK(s)"
    print(f"\n🎯 Completed {len(built)} {noun}:")
    for result in built:
        print(f"  📱 {result}")
    if failed:
        print(f"❌ Failed: {', '.join(failed)}")
        exit(1)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) == 2 else "all")
