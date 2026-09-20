import ipaddress
import re
from urllib.parse import urlparse

ALLOWED_EVIDENCE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".mp4", ".webm", ".mov",
    ".pdf", ".txt", ".json", ".html", ".eml",
}

ALLOWED_EVIDENCE_MIME_TYPES = {
    "image/png", "image/jpeg", "image/gif", "image/webp",
    "video/mp4", "video/webm", "video/quicktime",
    "application/pdf", "text/plain", "application/json", "text/html",
    "message/rfc822",
}

SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9._\- ]{1,255}$")


def is_valid_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def is_https(url: str) -> bool:
    return urlparse(url).scheme == "https"


def is_public_hostname(url: str) -> bool:
    """Reject URLs that resolve to loopback/private/link-local addresses to
    mitigate SSRF when the server later fetches a user-submitted URL for
    OSINT/preview purposes. This is a hostname-literal check; DNS resolution
    is validated again at fetch time in osint_service.
    """
    host = urlparse(url).hostname
    if not host:
        return False
    if host in ("localhost",):
        return False
    try:
        ip = ipaddress.ip_address(host)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast)
    except ValueError:
        return True  # not a literal IP; DNS-based SSRF check happens at fetch time


def sanitize_filename_extension(filename: str) -> str | None:
    if not filename:
        return None
    lowered = filename.lower()
    for ext in ALLOWED_EVIDENCE_EXTENSIONS:
        if lowered.endswith(ext):
            return ext
    return None


def is_safe_display_filename(filename: str) -> bool:
    return bool(SAFE_FILENAME_RE.match(filename)) and ".." not in filename and "/" not in filename and "\\" not in filename
