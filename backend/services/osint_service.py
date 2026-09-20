"""OSINT collection module — public-information-only.

This module fetches the PUBLICLY served HTML of a URL the operator
supplies (e.g. a public profile page) using a plain HTTPS GET, and
extracts only what a normal unauthenticated browser would see: page
title, meta description, and Open Graph tags. It does not:

  - authenticate as any user or bypass a login/paywall,
  - defeat CAPTCHAs or rate limiting,
  - read private messages, private posts, or non-public follower lists,
  - use leaked/stolen credentials.

If the target requires authentication or blocks the request, the
function returns a COULD_NOT_COLLECT status rather than attempting any
workaround. All output is provenance-tagged with the source URL and
collection time so it can become an Evidence record.
"""

import ipaddress
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from utils.validators import is_public_hostname, is_valid_http_url

USER_AGENT = "ReportValidatorOSINTBot/1.0 (+public-evidence-collection; contact: trust-safety-team)"
REQUEST_TIMEOUT = 10.0
MAX_RESPONSE_BYTES = 5 * 1024 * 1024


def _resolves_to_public_ip(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


def collect_public_page(url: str) -> dict:
    collected_at = datetime.now(timezone.utc)

    # These are expected, common outcomes (a malformed URL, a target that
    # resolves to a private/internal address) — reported as COULD_NOT_COLLECT
    # like any other collection failure, never raised past this function.
    if not is_valid_http_url(url):
        return {"status": "COULD_NOT_COLLECT", "reason": "URL is not a valid http(s) URL", "source_url": url, "collected_at": collected_at.isoformat()}
    if not is_public_hostname(url):
        return {"status": "COULD_NOT_COLLECT", "reason": "URL host is not a public address", "source_url": url, "collected_at": collected_at.isoformat()}

    hostname = urlparse(url).hostname
    if hostname and not _resolves_to_public_ip(hostname):
        return {
            "status": "COULD_NOT_COLLECT",
            "reason": "URL resolves to a non-public address; refusing to fetch (SSRF protection)",
            "source_url": url,
            "collected_at": collected_at.isoformat(),
        }
    try:
        with httpx.Client(follow_redirects=True, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            resp = client.get(url)
    except httpx.HTTPError as exc:
        return {
            "status": "COULD_NOT_COLLECT",
            "reason": f"Request failed: {exc}",
            "source_url": url,
            "collected_at": collected_at.isoformat(),
        }

    if resp.status_code in (401, 403, 429):
        return {
            "status": "COULD_NOT_COLLECT",
            "reason": f"Platform returned HTTP {resp.status_code} (login-walled, blocked, or rate-limited). "
                      "No bypass was attempted.",
            "source_url": url,
            "collected_at": collected_at.isoformat(),
        }
    if not resp.is_success:
        return {
            "status": "COULD_NOT_COLLECT",
            "reason": f"Platform returned HTTP {resp.status_code}",
            "source_url": url,
            "collected_at": collected_at.isoformat(),
        }

    content = resp.content[:MAX_RESPONSE_BYTES]
    soup = BeautifulSoup(content, "html.parser")

    def meta(name_or_prop: str) -> str | None:
        tag = soup.find("meta", attrs={"property": name_or_prop}) or soup.find("meta", attrs={"name": name_or_prop})
        return tag.get("content") if tag else None

    return {
        "status": "COLLECTED",
        "source_url": url,
        "final_url": str(resp.url),
        "collected_at": collected_at.isoformat(),
        "http_status": resp.status_code,
        "title": soup.title.string.strip() if soup.title and soup.title.string else None,
        "description": meta("description") or meta("og:description"),
        "og_title": meta("og:title"),
        "og_type": meta("og:type"),
        "og_site_name": meta("og:site_name"),
    }
