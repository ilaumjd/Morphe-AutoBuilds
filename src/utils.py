import os
import re
import shutil
import struct
import fnmatch
import logging
import zipfile
import subprocess
from typing import List, Optional
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs
from src import session, github_token

def _parseparam(s):
    while s[:1] == ";":
        s = s[1:]
        end = s.find(";")
        while end > 0 and (s.count('"', 0, end) - s.count('\\"', 0, end)) % 2:
            end = s.find(";", end + 1)
        if end < 0:
            end = len(s)
        f = s[:end]
        yield f.strip()
        s = s[end:]


def parse_header(line):
    """Parse a Content-type like header.
    Return the main content-type and a dictionary of options.
    """
    parts = _parseparam(";" + line)
    key = parts.__next__()
    pdict = {}
    for p in parts:
        i = p.find("=")
        if i >= 0:
            name = p[:i].strip().lower()
            value = p[i + 1 :].strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
                value = value.replace("\\\\", "\\").replace('\\"', '"')
            pdict[name] = value
    return key, pdict

def find_file(files: list[Path], suffix: str, contains: str = None) -> Path | None:
    """Return the first file with ``suffix`` whose name contains ``contains``."""
    for file in files:
        name = file.name.lower()
        if name.endswith(suffix) and (not contains or contains.lower() in name):
            return file
    return None

def find_apksigner() -> str | None:
    on_path = shutil.which("apksigner")
    if on_path:
        return on_path

    sdk_roots = [
        "/usr/local/lib/android/sdk",  # GitHub Actions runner default
        os.environ.get("ANDROID_HOME"),
        os.environ.get("ANDROID_SDK_ROOT"),
    ]

    for root in sdk_roots:
        if not root:
            continue
        build_tools_dir = Path(root) / "build-tools"
        if not build_tools_dir.exists():
            continue
        versions = sorted(build_tools_dir.iterdir(), reverse=True)
        for version_dir in versions:
            apksigner_path = version_dir / "apksigner"
            if apksigner_path.exists() and apksigner_path.is_file():
                return str(apksigner_path)

    logging.error(
        "No apksigner found. Install Android SDK build-tools and either put "
        "apksigner on PATH or set ANDROID_HOME/ANDROID_SDK_ROOT."
    )
    return None

def run_process(
    command: List[str],
    capture: bool = False,
    silent: bool = False,
    check: bool = True,
) -> Optional[str]:
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    output_lines = []
    for line in iter(process.stdout.readline, ''):
        if not silent:
            print(line.rstrip(), flush=True)
        if capture:
            output_lines.append(line)
    process.stdout.close()
    return_code = process.wait()

    output = ''.join(output_lines).strip() if capture else None

    if check and return_code != 0:
        # Include captured output so callers can diagnose and optionally retry.
        raise subprocess.CalledProcessError(return_code, command, output=output)

    return output

def normalize_version(version: str) -> list[int]:
    parts = version.split('.')
    normalized = []
    for part in parts:
        match = re.match(r'(\d+)', part)
        if match:
            normalized.append(int(match.group(1)))
        else:
            normalized.append(0)
    
    # Include build number in comparison for versions like "6.6 build 002"
    build_match = re.search(r'build\s+(\d+)', version, re.IGNORECASE)
    if build_match:
        normalized.append(int(build_match.group(1)))
    
    # Also check for parentheses format like "32.30.0(1575420)"
    paren_match = re.search(r'\((\d+)\)$', version)
    if paren_match:
        normalized.append(int(paren_match.group(1)))
    
    return normalized

# Version codes the patch bundle was written against, per package/version/ABI,
# as printed by `list-versions` (e.g. "[versionCodes: ARM64_V8A=384510827]").
_VERSION_CODES: dict[tuple[str, str, str], dict[str, str]] = {}
_ABI_NAMES = {"ARM64_V8A": "arm64-v8a", "ARMEABI_V7A": "armeabi-v7a", "X86_64": "x86_64", "X86": "x86"}


def get_version_code(package_name: str, patches: str, version: str, arch: str) -> Optional[str]:
    """Version code the patches target for ``version`` on ``arch``, if the CLI listed one.

    Only known after ``get_supported_versions`` ran for the same package and
    patch bundle.
    """
    return _VERSION_CODES.get((package_name, str(patches), version), {}).get(arch)


def get_supported_versions(package_name: str, cli: str, patches: str) -> Optional[list[str]]:
    """Return the app versions the patch bundle declares compatibility with.

    Returns:
        list[str]: specific compatible versions, highest first. The caller must
            build one of these and must NOT fall back to the store's latest.
        []: the CLI query succeeded but no specific versions were declared
            (patches are version-agnostic); building latest is safe.
        None: the CLI query itself failed, so patch compatibility is unknown.
            The caller must NOT build; guessing latest risks shipping a build
            with silently skipped patches.
    """
    # `list-versions` is lightweight but may only report the "most common"
    # versions; if it yields too little, fall back to parsing `list-patches`.
    cmd = [
        'java', '-jar', cli,
        'list-versions',
        '-f', package_name,
        '--patches', patches
    ]

    # We want the raw output even if the CLI returns a non-zero exit code (bad
    # args, missing patches, etc.) so we can decide what to do.
    output = run_process(cmd, capture=True, silent=True, check=False)

    if not output:
        logging.warning("No output returned from list-versions command")
        return None

    lines = output.splitlines()
    logging.info(f"CLI raw output lines: {lines}")

    # Detect CLI error/usage output (wrong syntax, unrecognized args, etc.)
    first_line = lines[0].strip().lower()
    if 'usage:' in first_line or 'unmatched argument' in first_line or 'error' in first_line:
        logging.warning("CLI returned error/usage output, cannot determine version")
        return None

    if len(lines) <= 2:
        logging.warning("Output has no version lines")
        return []

    versions = []
    for line in lines[2:]:
        line = line.strip()
        if line and 'Any' not in line:
            # Parse version - may include "build XXX" suffix
            # Format: "6.6 build 002" or "32.30.0(1575420)" or just "6.6"
            parts = line.split()
            if parts:
                version = parts[0]
                # Validate it looks like a version (starts with a digit)
                if not version[0].isdigit():
                    continue
                codes = re.search(r"\[versionCodes:\s*([^\]]+)\]", line)
                if codes:
                    pairs = (item.split("=", 1) for item in codes.group(1).split(",") if "=" in item)
                    _VERSION_CODES[(package_name, str(patches), version)] = {
                        _ABI_NAMES.get(abi.strip().upper(), abi.strip().lower()): code.strip()
                        for abi, code in pairs
                    }
                # Check if next parts are "build XXX"
                if len(parts) >= 3 and parts[1].lower() == 'build':
                    version = f"{parts[0]} build {parts[2]}"
                versions.append(version)

    # If Morphe CLI only returned a tiny "most common" list (or nothing),
    # attempt to derive a fuller candidate set from `list-patches`.
    if len(versions) <= 1:
        try:
            alt_cmd = [
                "java", "-jar", cli,
                "list-patches",
                "--with-packages",
                "--with-versions",
                patches,
            ]
            alt_out = run_process(alt_cmd, capture=True, silent=True, check=False) or ""
            derived: list[str] = []
            for ln in alt_out.splitlines():
                if package_name not in ln:
                    continue
                # Grab any versions mentioned on the same line as the package name.
                for m in re.finditer(r"\d+(?:\.\d+)+(?:\(\d+\))?", ln):
                    derived.append(m.group(0))
            if derived:
                versions.extend(derived)
        except Exception:
            pass

    if not versions:
        logging.warning("No supported versions found")
        return []

    # Sort highest -> lowest.
    versions = sorted(set(versions), key=normalize_version, reverse=True)
    logging.info(f"CLI parsed versions: {versions}")
    return versions


def extract_filename(response, fallback_url=None) -> str:
    cd = response.headers.get('content-disposition')
    if cd:
        _, params = parse_header(cd)
        filename = params.get('filename') or params.get('filename*')
        if filename:
            return unquote(filename)

    parsed = urlparse(response.url)
    query_params = parse_qs(parsed.query)
    rcd = query_params.get('response-content-disposition')
    if rcd:
        _, params = parse_header(unquote(rcd[0]))
        filename = params.get('filename') or params.get('filename*')
        if filename:
            return unquote(filename)

    path = urlparse(fallback_url or response.url).path
    return unquote(Path(path).name)

def detect_github_release(user: str, repo: str, tag: str = "latest") -> dict:
    """Return the GitHub release for ``tag``: "latest", "prerelease" (newest
    pre-release) or an explicit tag name."""
    api = f"https://api.github.com/repos/{user}/{repo}/releases"
    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    if tag == "latest":
        url = f"{api}/latest"
    elif tag == "prerelease":
        url = api
    else:
        url = f"{api}/tags/{tag}"

    logging.info(f"Fetching release {tag} for {user}/{repo}...")
    response = session.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    if tag == "prerelease":
        prereleases = [r for r in data if r.get("prerelease")]
        if not prereleases:
            raise ValueError(f"No prerelease found for {user}/{repo}")
        data = max(prereleases, key=lambda r: r["created_at"])

    return data

def strip_zip_entries(zip_path: Path, patterns: list[str]) -> None:
    """Strip matching file patterns from a ZIP archive in a cross-platform way."""
    if not zip_path or not zip_path.exists():
        return

    if shutil.which("zip"):
        try:
            run_process(["zip", "--delete", str(zip_path)] + patterns, silent=True, check=False)
            return
        except Exception:
            pass

    # Pure Python fallback using zipfile
    temp_zip = zip_path.with_suffix(".tmp.zip")
    try:
        modified = False
        with zipfile.ZipFile(zip_path, 'r') as zin:
            with zipfile.ZipFile(temp_zip, 'w', compression=zin.compression) as zout:
                for item in zin.infolist():
                    if any(fnmatch.fnmatch(item.filename, p) for p in patterns):
                        modified = True
                        continue
                    zout.writestr(item, zin.read(item.filename))
        if modified:
            zip_path.unlink()
            temp_zip.rename(zip_path)
        else:
            temp_zip.unlink(missing_ok=True)
    except Exception as e:
        logging.debug(f"Failed to strip zip entries: {e}")
        if temp_zip.exists():
            temp_zip.unlink(missing_ok=True)


def check_apk_integrity(apk_path: Path) -> bool:
    """Validate that APK is a valid uncorrupted zip archive."""
    if not apk_path or not apk_path.exists() or apk_path.stat().st_size == 0:
        return False
    try:
        if not zipfile.is_zipfile(apk_path):
            return False
        with zipfile.ZipFile(apk_path, 'r') as z:
            bad_file = z.testzip()
            if bad_file is not None:
                return False
        return True
    except Exception:
        return False


def is_apk_signed(apk_path: Path) -> bool:
    """Return True if the APK carries an Android signature (v1 or v2+).

    Checks for v1 (JAR signing) META-INF/*.RSA|*.DSA|*.EC entries first,
    then looks for an APK Signing Block containing a v2/v3 signature
    scheme id. This only reports whether a signature is present;
    ``ensure_usable_apk`` treats its absence as a warning, not a failure.
    """
    if not apk_path or not apk_path.exists():
        return False
    try:
        with zipfile.ZipFile(apk_path, 'r') as z:
            names = z.namelist()
            for n in names:
                upper = n.upper()
                if upper.startswith("META-INF/") and (
                    upper.endswith(".RSA") or upper.endswith(".DSA") or upper.endswith(".EC")
                ):
                    return True
    except Exception:
        return False
    # No v1 signature: look for the APK Signing Block (v2/v3/v3.1).
    try:
        sig_block_magic = b"APK Sig Block 42"
        v2_scheme_ids = {0x7109871A, 0xF05368A0, 0x1B93AD61}  # v2, v3, v3.1
        with open(apk_path, "rb") as f:
            f.seek(0, 2)
            file_size = f.tell()
            # EOCD is at the very end; central directory offset lives at +16.
            tail = min(file_size, 65558)
            f.seek(file_size - tail)
            buf = f.read(tail)
            eocd_pos = buf.rfind(b"PK\x05\x06")
            if eocd_pos < 0:
                return False
            cd_offset = struct.unpack("<I", buf[eocd_pos + 16:eocd_pos + 20])[0]
            if cd_offset < 32 or cd_offset > file_size:
                return False
            f.seek(cd_offset - 24)
            header = f.read(24)
            if len(header) < 24 or header[8:] != sig_block_magic:
                return False
            block_size = struct.unpack("<Q", header[:8])[0]
            f.seek(cd_offset - 24 - block_size + 8)
            remaining = block_size - 8
            while remaining >= 12:
                pair = f.read(12)
                if len(pair) < 12:
                    break
                pair_size, pair_id = struct.unpack("<QI", pair[:12])
                if pair_id in v2_scheme_ids:
                    return True
                skip = pair_size - 4
                if skip < 0:
                    break
                f.seek(skip, 1)
                remaining -= 12 + skip
    except Exception:
        pass
    return False


def ensure_usable_apk(apk_path: Path, app_name: str, version: str) -> Path | None:
    """Return ``apk_path`` if it passes the integrity check.

    Otherwise attempt a ``zip -FF`` repair and re-check.  A file that is
    still corrupt afterwards is deleted and ``None`` is returned so the
    caller can try another download source instead of feeding a broken APK
    to the patcher (which crashes with an obscure NPE).

    A missing Android signature is only a warning: some stores serve intact
    APKs without a v1/v2/v3 signature, the Morphe patcher accepts them and
    signs its own output, and the check never verified who signed the file
    anyway.
    """
    def _good(path: Path) -> bool:
        if not check_apk_integrity(path):
            return False
        if not is_apk_signed(path):
            logging.warning(
                f"APK {path.name} carries no v1/v2/v3 signature; accepting it because "
                "it is intact and the patcher re-signs its output")
        return True

    if _good(apk_path):
        return apk_path

    logging.warning(f"APK integrity check failed for {apk_path.name}; attempting repair with zip -FF")
    if not shutil.which("zip"):
        logging.warning("zip command not available for repair")
        apk_path.unlink(missing_ok=True)
        return None

    fixed_apk = apk_path.with_name(f"{app_name}-fixed-v{version}.apk")
    fixed_apk.unlink(missing_ok=True)
    try:
        subprocess.run(
            ["zip", "-FF", str(apk_path), "--out", str(fixed_apk)],
            check=False, capture_output=True, timeout=120,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        logging.warning("zip -FF repair timed out; discarding download")
        apk_path.unlink(missing_ok=True)
        fixed_apk.unlink(missing_ok=True)
        return None
    if not (fixed_apk.exists() and fixed_apk.stat().st_size > 0):
        logging.warning("Repair produced no usable file; discarding download")
        apk_path.unlink(missing_ok=True)
        return None

    apk_path.unlink(missing_ok=True)
    fixed_apk.rename(apk_path)
    if _good(apk_path):
        logging.info("APK repaired successfully and passes the integrity check")
        return apk_path

    logging.warning("APK still fails checks after zip -FF repair; discarding download")
    apk_path.unlink(missing_ok=True)
    return None
