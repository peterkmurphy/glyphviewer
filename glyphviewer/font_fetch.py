# Glyphviewer: a tool to examine web fonts online.
# Copyright (c) 2011-2026 Peter Murphy <peterkmurphy@gmail.com>
#
# Redistribution and use permitted under the BSD-3-Clause terms in LICENSE.txt.

from __future__ import annotations

import ipaddress
import socket
import tempfile
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
}


class FontFetchError(Exception):
    pass


class FontTooLargeError(FontFetchError):
    pass


class FontTimeoutError(FontFetchError):
    pass


class UnsafeFontURLError(FontFetchError):
    pass


def _hostname_blocked(hostname: str) -> bool:
    host = hostname.lower().rstrip(".")
    if not host:
        return True
    if host in BLOCKED_HOSTNAMES:
        return True
    return host.endswith((".local", ".internal"))


def _ip_blocked(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolve_host_ips(hostname: str) -> list[ipaddress._BaseAddress]:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeFontURLError(f"Could not resolve hostname: {hostname}") from exc

    ips: list[ipaddress._BaseAddress] = []
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if _ip_blocked(ip):
            raise UnsafeFontURLError(f"Blocked address for hostname: {hostname}")
        ips.append(ip)
    return ips


def validate_remote_font_url(url: str) -> None:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeFontURLError("Only http and https font URLs are allowed.")
    if parsed.username or parsed.password:
        raise UnsafeFontURLError("Font URLs must not include credentials.")
    if not parsed.hostname:
        raise UnsafeFontURLError("Font URL is missing a hostname.")
    if _hostname_blocked(parsed.hostname):
        raise UnsafeFontURLError("Font URL hostname is not allowed.")
    try:
        ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        _resolve_host_ips(parsed.hostname)
    else:
        if _ip_blocked(ip):
            raise UnsafeFontURLError("Font URL hostname is not allowed.")


def fetch_remote_font(url: str, *, max_size: int, timeout: int) -> tuple[str, dict[str, str]]:
    validate_remote_font_url(url)
    request = Request(
        url,
        headers={"User-Agent": "pkmurphy-glyphviewer/1.0"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            headers = {key.lower(): value for key, value in response.headers.items()}
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_size:
                    raise FontTooLargeError(f"Remote font exceeds {max_size} bytes.")
                chunks.append(chunk)
    except TimeoutError as exc:
        raise FontTimeoutError("Remote font request timed out.") from exc
    except URLError as exc:
        raise FontFetchError("Remote font could not be retrieved.") from exc

    suffix = ".woff2"
    lower_url = url.lower()
    for ext in (".woff2", ".woff", ".otf", ".ttf"):
        if lower_url.endswith(ext):
            suffix = ext
            break

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp.write(b"".join(chunks))
        return temp.name, headers
