"""GitHub releases as a store for original APKs.

For apps whose vendor publishes APKs on GitHub (e.g. Brave). An app opts in with
``apps/github/<app>.json`` and then uses *only* GitHub: no other store is tried.

    {
      "package": "com.brave.browser",
      "repo": "brave/brave-browser",
      "tag": "v{version}",
      "assets": { "arm64-v8a": "BraveMonoarm64.apk", "armeabi-v7a": "BraveMonoarm.apk" }
    }

``tag`` is the release tag of a version (``{version}`` is replaced; default
``{version}``) and ``assets`` maps an architecture to the asset name. An asset
named ``<asset>.sha256`` next to the APK, when published, is used to verify the
download before it is stored. An architecture without an asset is not served,
so a missing build fails instead of falling back to a different ABI.
"""
import logging
import re

from src import github_token, session

_releases: dict[tuple[str, str], dict] = {}


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    return headers


def _tag(version: str, config: dict) -> str:
    return (config.get("tag") or "{version}").replace("{version}", version)


def _release(repo: str, tag: str) -> dict | None:
    key = (repo, tag)
    if key not in _releases:
        url = f"https://api.github.com/repos/{repo}/releases/" + ("latest" if tag == "latest" else f"tags/{tag}")
        try:
            response = session.get(url, headers=_headers(), timeout=30)
            response.raise_for_status()
            _releases[key] = response.json()
        except Exception as e:
            logging.warning(f"GitHub release {tag} of {repo} not available: {e}")
            return None
    return _releases[key]


def _asset(release: dict, name: str) -> dict | None:
    return next((a for a in release.get("assets", []) if a["name"] == name), None)


def get_latest_version(app_name: str, config: dict) -> str | None:
    repo = config.get("repo")
    release = _release(repo, "latest") if repo else None
    if not release:
        return None
    prefix, _, suffix = (config.get("tag") or "{version}").partition("{version}")
    tag = release["tag_name"]
    if tag.startswith(prefix) and tag.endswith(suffix):
        return tag[len(prefix):len(tag) - len(suffix) or None]
    return tag


def get_download_link(version: str, app_name: str, config: dict) -> str | None:
    repo = config.get("repo")
    asset_name = (config.get("assets") or {}).get(config.get("arch") or "universal")
    if not repo or not asset_name:
        logging.warning(f"{app_name}: no GitHub asset configured for {config.get('arch') or 'universal'}")
        return None
    release = _release(repo, _tag(version, config))
    asset = _asset(release, asset_name) if release else None
    if not asset:
        logging.warning(f"{app_name}: asset {asset_name} not found in {repo} release {_tag(version, config)}")
        return None
    return asset["browser_download_url"]


def get_checksum(version: str, app_name: str, config: dict) -> str | None:
    """SHA-256 published for the asset, or None when the release has none."""
    repo = config.get("repo")
    asset_name = (config.get("assets") or {}).get(config.get("arch") or "universal")
    release = _release(repo, _tag(version, config)) if repo and asset_name else None
    sidecar = _asset(release, f"{asset_name}.sha256") if release else None
    if not sidecar:
        logging.warning(f"{app_name}: no .sha256 published for {asset_name}; download will not be verified")
        return None
    try:
        text = session.get(sidecar["browser_download_url"], headers=_headers(), timeout=30).text
    except Exception as e:
        logging.warning(f"{app_name}: could not read {sidecar['name']}: {e}")
        return None
    match = re.search(r"\b[0-9a-fA-F]{64}\b", text)
    return match.group(0).lower() if match else None
