import json
import logging
import re
import os
import zipfile
from sys import exit
from pathlib import Path
from os import getenv
import subprocess
from src import (
    utils,
    downloader
)

KEYSTORE = {
    "path": getenv("KEYSTORE_PATH", "keystore/public.jks"),
    "password": getenv("KEYSTORE_PASSWORD", "public"),
    "alias": getenv("KEYSTORE_ALIAS", "public"),
}

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

def download_apk(app_name: str, cli: Path, patches: Path, arch: str):
    """Try each store in order; return (apk, version, candidates, platform)."""
    for platform in downloader.PLATFORMS:
        apk_path, ver, cands = downloader.download_platform(app_name, platform, str(cli), str(patches), arch)
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

def run_build(app_name: str, source: str, arch: str, cli: Path, patches: Path, name: str) -> str | None:
    """Download, patch and sign one app for one architecture."""
    input_apk, version, candidates, platform = download_apk(app_name, cli, patches, arch)
    if input_apk is None or not version:
        logging.error(f"❌ Failed to download APK for {app_name} from every store")
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
                app_name, platform, str(cli), str(patches), arch, override_version=ver
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

        signed_apk = Path("dist") / f"{app_name}-{arch}-{name}-v{version}.apk"
        signed_apk.parent.mkdir(exist_ok=True)
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
    if arch:
        entries = [{**e, "arches": [arch]} for e in entries]
    return entries

def main():
    entries = load_entries()
    if not entries or any(not e.get("source") for e in entries):
        logging.error("No matching entries in patch-config.json (set SOURCE for ad-hoc builds)")
        exit(1)

    tools: dict[str, tuple[Path, Path, str]] = {}
    built, failed = [], []

    for entry in entries:
        app_name, source = entry["app_name"], entry["source"]
        for arch in entry.get("arches") or ["universal"]:
            label = f"{app_name}/{source}/{arch}"
            logging.info(f"🔨 Building {label}...")
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

                apk_path = run_build(app_name, source, arch, *tools[source])
            except Exception as e:
                logging.error(f"❌ {label} failed: {e}")
                apk_path = None

            (built if apk_path else failed).append(apk_path or label)

    print(f"\n🎯 Built {len(built)} APK(s):")
    for apk in built:
        print(f"  📱 {apk}")
    if failed:
        print(f"❌ Failed: {', '.join(failed)}")
        exit(1)

if __name__ == "__main__":
    main()
