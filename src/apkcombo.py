"""APKCombo store (https://apkcombo.com), a last-resort fallback.

Used only by apps that opt in with an ``apps/apkcombo/<app>.json`` file
(``{ "package": "<package>", "version": "<pinned version>" }``). Download pages
are public: ``/search/<package>/download/phone-<version>-<apk|xapk|apks>``.
Their links are either embedded (``a.variant``) or loaded by a small POST to
``<app>/<xid>/dl``; both are handled here.

Adapted from RookieEnough/Morphe-AutoBuilds (src/apkcombo.py).
"""
from __future__ import annotations

import logging
import re
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests as plain_requests
from bs4 import BeautifulSoup

from src import session, trawl, utils

BASE_URL = "https://apkcombo.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36"}


class _Page:
    def __init__(self, url: str, text: str, content: bytes):
        self.url, self.text, self.content = url, text, content


def _get(url: str) -> _Page | None:
    """Fetch a page: the impersonating session first, then plain requests, then trawl."""
    for fetch in (session.get, plain_requests.get):
        try:
            response = fetch(url, headers=HEADERS, timeout=25)
            if response.status_code == 200 and response.content:
                return _Page(str(response.url), response.text, response.content)
        except Exception as exc:
            logging.debug("APKCombo request failed for %s: %s", url, exc)
    rendered = trawl.fetch(url)
    return _Page(rendered.url, rendered.text, rendered.content) if rendered else None


def _unwrap_redirect(url: str) -> str:
    parsed = urlparse(url)
    if parsed.path == "/r2":
        target = parse_qs(parsed.query).get("u", [""])[0]
        if target:
            return unquote(target)
    return url


def _variant_link(soup: BeautifulSoup, base_url: str) -> str | None:
    for anchor in soup.select("a.variant[href]"):
        href = anchor.get("href")
        if href:
            return _unwrap_redirect(urljoin(base_url, href))
    return None


def _dynamic_link(page: _Page, package: str) -> str | None:
    """Resolve the download tab APKCombo loads with JavaScript."""
    xid = re.search(r'\bxid\s*=\s*["\']([^"\']+)', page.text)
    if not xid:
        return None
    app_path = re.sub(r"/download(?:/[^/?#]+)?/?(?:[?#].*)?$", "/", urlparse(page.url).path)
    if not app_path.endswith("/"):
        app_path += "/"
    endpoint = urljoin(page.url, f"{app_path.lstrip('/')}{xid.group(1)}/dl")
    kwargs = {
        "data": {"package_name": package, "version": ""},
        "headers": {**HEADERS, "Referer": page.url, "X-Requested-With": "XMLHttpRequest"},
        "timeout": 25,
    }
    for post in (session.post, plain_requests.post):
        try:
            fragment = post(endpoint, **kwargs)
            fragment.raise_for_status()
        except Exception as exc:
            logging.debug("APKCombo dynamic request failed for %s: %s", package, exc)
            continue
        link = _variant_link(BeautifulSoup(fragment.content, "html.parser"), str(fragment.url))
        if link:
            return link
    return None


def get_latest_version(app_name: str, config: dict) -> str | None:
    package = (config.get("package") or "").strip()
    page = _get(f"{BASE_URL}/search/{package}/download") if package else None
    if not page:
        return None
    versions = [v for v in re.findall(r"phone-([0-9][^-]*)-(?:apk|xapk|apks)", page.text) if v and v[0].isdigit()]
    return max(versions, key=utils.normalize_version) if versions else None


def get_download_link(version: str, app_name: str, config: dict) -> str | None:
    package = (config.get("package") or "").strip()
    if not package or not version:
        return None
    for extension in ("apk", "xapk", "apks"):
        page = _get(f"{BASE_URL}/search/{package}/download/phone-{version}-{extension}")
        if not page:
            continue
        link = _variant_link(BeautifulSoup(page.content, "html.parser"), page.url) or _dynamic_link(page, package)
        if link:
            return link
    logging.warning(f"APKCombo: no download link for {app_name} v{version}")
    return None
