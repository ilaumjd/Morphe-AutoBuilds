import hashlib
import json
import logging
import importlib
import os
import shutil
import zipfile
from pathlib import Path
from src import utils, session
from src.paths import ORIGINAL_APKS_DIR, ORIGINAL_SUFFIXES, original_candidates, original_stem


# Download stores, in the order they are tried.
PLATFORMS = ["apkmirror", "aptoide", "uptodown", "apkpure"]


def platforms_for(app_name: str) -> list[str]:
    """Stores to try for an app: GitHub alone when the app has an apps/github
    config (its vendor publishes the APKs there), otherwise the app stores."""
    if (Path("apps") / "github" / f"{app_name}.json").exists():
        return ["github"]
    return PLATFORMS


class UnknownPatchCompatibilityError(ValueError):
    """Raised when the patch CLI cannot tell us which app versions the patches
    support. Building the store's latest in this situation risks shipping a
    build with silently skipped patches, so the build must fail loudly instead
    of falling back to latest."""

def download_resource(url: str, name: str = None) -> Path:
    res = session.get(url, stream=True)
    res.raise_for_status()
    final_url = res.url

    if not name:
        name = utils.extract_filename(res, fallback_url=final_url)

    filepath = Path(name)
    total_size = int(res.headers.get('content-length', 0))
    downloaded_size = 0

    with filepath.open("wb") as file:
        for chunk in res.iter_content(chunk_size=8192):
            if chunk:
                file.write(chunk)
                downloaded_size += len(chunk)

    logging.info(
        f"URL: {final_url} [{downloaded_size}/{total_size}] -> \"{filepath}\" [1]"
    )

    return filepath


def cached_apk(app_name: str, version: str, arch: str) -> Path | None:
    """Copy a stored original APK (apks/original/<app>-<arch>-original-v<version>.<ext>)
    into the working directory, if available."""
    for cached in original_candidates(app_name, arch, version):
        if not cached.is_file():
            continue
        if zipfile.is_zipfile(cached):
            destination = Path(cached.name)
            shutil.copy2(cached, destination)
            logging.info(f"Using cached original APK: {cached}")
            return destination
        # Originals are never deleted by the pipeline; a bad file is skipped
        # (and replaced only if the same name is downloaded again).
        logging.warning(f"Ignoring unreadable cached original APK: {cached}")
    return None


def download_cached_apk(
    url: str, app_name: str, version: str, arch: str, sha256: str | None = None
) -> Path:
    """Download a base APK once and reuse it from the persistent local cache.

    ``apks/original/`` is deliberately the default so local builds keep their
    original, unmodified downloads without requiring an environment variable.
    The cache is copied into the working directory because patching mutates its
    input file.
    """
    cached = cached_apk(app_name, version, arch)
    if cached:
        return cached

    cache_dir = ORIGINAL_APKS_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    downloaded = download_resource(url)
    if sha256:
        digest = hashlib.sha256()
        with downloaded.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                digest.update(chunk)
        if digest.hexdigest() != sha256.lower():
            downloaded.unlink(missing_ok=True)
            raise ValueError(
                f"SHA-256 mismatch for {downloaded.name}: expected {sha256}, got {digest.hexdigest()}"
            )
        logging.info(f"SHA-256 verified for {downloaded.name}")
    if downloaded.suffix.lower() in ORIGINAL_SUFFIXES:
        cached = cache_dir / f"{original_stem(app_name, arch, version)}{downloaded.suffix.lower()}"
        shutil.copy2(downloaded, cached)
        logging.info(f"Saved original APK: {cached}")
    return downloaded

def download_required(source: str) -> tuple[list[Path], str]:
    """Download the CLI (.jar) and patch bundle (.mpp) listed in sources/<source>.json."""
    source_path = Path("sources") / f"{source}.json"
    with source_path.open() as json_file:
        repos_info = json.load(json_file)

    name = repos_info[0]["name"]
    downloaded_files = []

    for repo_info in repos_info[1:]:
        release = utils.detect_github_release(
            repo_info["user"], repo_info["repo"], repo_info.get("tag", "latest")
        )
        logging.info(f"{repo_info['user']}/{repo_info['repo']}: {release['tag_name']}")
        for asset in release["assets"]:
            if asset["name"].endswith((".jar", ".mpp")):
                downloaded_files.append(download_resource(asset["browser_download_url"]))

    return downloaded_files, name

def download_apkeditor() -> Path:
    release = utils.detect_github_release("REAndroid", "APKEditor", "latest")

    for asset in release["assets"]:
        if asset["name"].startswith("APKEditor") and asset["name"].endswith(".jar"):
            return download_resource(asset["browser_download_url"])

    raise RuntimeError("APKEditor .jar file not found in the latest release")

def download_platform(
    app_name: str,
    platform: str,
    cli: str,
    patches: str,
    arch: str = None,
    override_version: str = None,
    cached_only: bool = False,
    universal_fallback: bool = False,
) -> tuple[Path | None, str | None, list[str]]:
    try:
        config_path = Path("apps") / platform / f"{app_name}.json"
        config = None
        if config_path.exists():
            with config_path.open() as json_file:
                config = json.load(json_file)
        else:
            # Fallback: search other platform config directories for this app
            for other_platform in PLATFORMS:
                if other_platform == platform:
                    continue
                other_path = Path("apps") / other_platform / f"{app_name}.json"
                if other_path.exists():
                    try:
                        with other_path.open() as json_file:
                            other_cfg = json.load(json_file)
                        if other_cfg.get("package"):
                            config = {
                                "name": other_cfg.get("name", app_name),
                                "package": other_cfg["package"],
                                "version": other_cfg.get("version", ""),
                                "arch": other_cfg.get("arch", "universal"),
                                "type": other_cfg.get("type", "APK"),
                                "dpi": other_cfg.get("dpi", "nodpi"),
                                "org": other_cfg.get("org", app_name),
                                "download_url": other_cfg.get("download_url"),
                            }
                            logging.info(f"Synthesized {platform} config for {app_name} from {other_platform}")
                            break
                    except Exception:
                        continue

        if not config or not config.get("package"):
            raise FileNotFoundError(f"Config file not found for {app_name} on {platform}")
        
        # Override arch only if explicitly specified non-universal, or if config has no arch set.
        # An entry that is explicitly universal keeps the arch from the app config; only the
        # universal retry after a failed ARM64 attempt (universal_fallback) really asks the
        # stores for a universal variant, instead of repeating the config's ARM64 request.
        if arch and arch != "universal":
            config['arch'] = arch
        elif universal_fallback:
            config['arch'] = "universal"
            config['universal_fallback'] = True
        elif 'arch' not in config or not config['arch']:
            config['arch'] = arch or "universal"

        platform_module = importlib.import_module(f"src.{platform}")

        # A direct link is useful when a store blocks automated scraping or
        # when an operator has obtained a known-good original APK manually.
        # APK_URL is a one-off override; download_url persists with the app
        # configuration and takes priority for that app.
        direct_url = config.get("download_url") or os.getenv("APK_URL")
        if direct_url:
            version = override_version or (config.get("version") or "").strip()
            if not version:
                raise ValueError(
                    f"A direct APK URL for {app_name} requires a pinned version in its config"
                )
            cached = cached_apk(app_name, version, arch or "universal")
            if cached:
                return cached, version, [version]
            if cached_only:
                raise FileNotFoundError(
                    f"Original APK is not cached: {app_name} v{version} ({arch or 'universal'})"
                )
            return download_cached_apk(direct_url, app_name, version, arch or "universal"), version, [version]

        # Candidate versions (highest -> lowest):
        # - If config pins a version: only try that.
        # - Else if override provided (retry path): try only that.
        # - Else ask the patching CLI for compatible versions and try those.
        #
        # Policy: build ONLY what the patches declare compatibility with.
        # The store's latest version is NEVER appended as a fallback: if the
        # patches target specific versions and none of them are downloadable,
        # building latest would ship with patches silently skipped. Fail loudly
        # instead. Latest is only used when the patches are version-agnostic
        # (CLI query succeeded but declared no specific versions).
        pinned = (config.get("version") or "").strip()
        if override_version:
            candidates = [override_version]
        elif pinned:
            candidates = [pinned]
        else:
            compat = utils.get_supported_versions(config["package"], cli, patches)
            if compat is None:
                raise UnknownPatchCompatibilityError(
                    f"Cannot determine patch-compatible versions for {app_name} "
                    f"(package {config['package']}); refusing to fall back to "
                    f"latest to avoid shipping a build with silently skipped patches."
                )
            elif compat:
                candidates = compat
            else:
                try:
                    latest = platform_module.get_latest_version(app_name, config)
                except Exception as e:
                    logging.debug(f"Could not get latest version for {app_name} on {platform}: {e}")
                    latest = None
                candidates = [latest] if latest else []

        last_error: Exception | None = None
        for version in candidates:
            if not version:
                continue
            # Prefer an original that is already stored: no store lookup needed.
            cached = cached_apk(app_name, version, arch or "universal")
            if cached:
                return cached, version, candidates
            if cached_only:
                last_error = FileNotFoundError(
                    f"Original APK is not cached: {app_name} v{version} ({arch or 'universal'})"
                )
                continue
            if config.get('match_version_code'):
                # Apps whose store variants differ per build (e.g. Instagram): pick the
                # exact build the patches were written against.
                code = utils.get_version_code(config["package"], patches, version, config.get("arch", ""))
                if code:
                    config['version_code'] = code
                else:
                    config.pop('version_code', None)
            download_link = platform_module.get_download_link(version, app_name, config)
            if not download_link:
                last_error = ValueError(f"No download link found for {app_name} version {version}")
                continue
            try:
                checksum_of = getattr(platform_module, "get_checksum", None)
                checksum = checksum_of(version, app_name, config) if checksum_of else None
                filepath = download_cached_apk(
                    download_link, app_name, version, arch or "universal", sha256=checksum
                )
                return filepath, version, candidates
            except Exception as e:
                last_error = e
                continue

        raise last_error or ValueError(f"No downloadable versions found for {app_name} on {platform}")

    except UnknownPatchCompatibilityError:
        # Policy refusal: never swallow this as a download error. The build
        # must fail loudly so the version mismatch gets fixed instead of
        # shipping a broken latest build.
        raise
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return None, None, []
