"""APKPure store.

apkpure.com sits behind Cloudflare, so pages are rendered through trawl when it
is available and fetched directly otherwise. A download page exposes its file
(usually an XAPK bundle) as ``a#download_link`` and the version it shows in
``span.info-sdk``.
"""
import logging

from bs4 import BeautifulSoup

from src import session, trawl

BASE_URL = "https://apkpure.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': f'{BASE_URL}/',
}


def _page(url: str) -> BeautifulSoup | None:
    """Return the parsed page, via trawl first and a plain request as fallback."""
    rendered = trawl.fetch(url)
    if rendered:
        return BeautifulSoup(rendered.content, "html.parser")
    try:
        response = session.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        logging.warning(f"APKPure request failed for {url}: {e}")
        return None
    return BeautifulSoup(response.content, "html.parser")


def get_latest_version(app_name: str, config: dict) -> str | None:
    soup = _page(f"{BASE_URL}/{config['name']}/{config['package']}/versions")
    if soup:
        latest = soup.find('div', class_='ver-top-down')
        if latest and latest.get('data-dt-version'):
            return latest['data-dt-version']
    logging.error(f"Failed to fetch latest version for {app_name} from APKPure")
    return None


def get_download_link(version: str, app_name: str, config: dict) -> str | None:
    soup = _page(f"{BASE_URL}/{config['name']}/{config['package']}/download/{version}")
    if not soup:
        return None

    # An unknown version must not silently turn into whatever APKPure shows
    # instead: the page has to be for exactly the requested version.
    shown = soup.find('span', class_='info-sdk')
    shown_version = shown.get_text(strip=True) if shown else ""
    if shown_version.lower() != version.strip().lower():
        logging.warning(
            f"APKPure shows {shown_version or 'no version'} instead of {version} for {app_name}"
        )
        return None

    link = soup.find('a', id='download_link')
    href = link.get('href', '') if link else ''
    if href.startswith('http'):
        return href
    logging.warning(f"APKPure has no download link for {app_name} v{version}")
    return None
