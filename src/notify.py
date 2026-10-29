"""Immediate ntfy alerts from the build pipeline (separate from the end-of-run summary).

Uses NTFY_URL, NTFY_TOPIC and NTFY_TOKEN from the environment. Without NTFY_URL nothing is sent.
A failed alert never breaks the build.
"""

from __future__ import annotations

import logging
import os
from urllib.request import Request, urlopen


def alert(title: str, body: str, priority: str = "high") -> None:
    base = os.getenv("NTFY_URL", "").rstrip("/")
    if not base:
        return
    topic = os.getenv("NTFY_TOPIC", "morphe")
    headers = {"Title": title, "Priority": priority, "Tags": "warning"}
    token = os.getenv("NTFY_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urlopen(Request(f"{base}/{topic}", data=body.encode("utf-8"), headers=headers, method="POST"), timeout=20):
            pass
    except Exception as error:  # never let an alert break the build
        logging.warning(f"ntfy alert failed: {error}")
