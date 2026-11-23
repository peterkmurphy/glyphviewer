# Glyphviewer: a tool to examine web fonts online.
# Copyright (c) 2011-2026 Peter Murphy <peterkmurphy@gmail.com>
#
# Redistribution and use permitted under the BSD-3-Clause terms in LICENSE.txt.

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
import tempfile
from urllib.parse import urljoin, urlparse

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
}

MAX_REDIRECTS = 3


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
    if not ips:
        raise UnsafeFontURLError(f"Could not resolve hostname: {hostname}")
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


def _connect_host(ip: ipaddress._BaseAddress) -> str:
    return str(ip) if ip.version == 4 else f"[{ip}]"


def _request_path(parsed) -> str:
    path = parsed.path or "/"
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path


def _open_pinned_connection(url: str, *, timeout: int):
    """Open HTTP(S) to a validated IP while preserving Host/SNI for the hostname."""
    validate_remote_font_url(url)
    parsed = urlparse(url.strip())
    hostname = parsed.hostname
    assert hostname is not None

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = _resolve_host_ips(hostname)[0]
        server_hostname = hostname
    else:
        server_hostname = None

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    connect_host = _connect_host(ip)
    path = _request_path(parsed)
    headers = {
        "User-Agent": "pkmurphy-glyphviewer/1.0",
        "Host": hostname,
    }

    if parsed.scheme == "https":
        context = ssl.create_default_context()
        conn: http.client.HTTPConnection = http.client.HTTPSConnection(
            connect_host,
            port=port,
            timeout=timeout,
            context=context,
        )
        # Connect to the pinned IP but use the original hostname for SNI/certs.
        sock = socket.create_connection((str(ip), port), timeout=timeout)
        conn.sock = context.wrap_socket(sock, server_hostname=server_hostname or hostname)
    else:
        conn = http.client.HTTPConnection(connect_host, port=port, timeout=timeout)

    try:
        conn.request("GET", path, headers=headers)
        return conn, conn.getresponse()
    except Exception:
        conn.close()
        raise


def _read_limited(response: http.client.HTTPResponse, max_size: int) -> bytes:
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
    return b"".join(chunks)


def fetch_remote_font(url: str, *, max_size: int, timeout: int) -> tuple[str, dict[str, str]]:
    current = url.strip()
    for _hop in range(MAX_REDIRECTS + 1):
        try:
            conn, response = _open_pinned_connection(current, timeout=timeout)
        except TimeoutError as exc:
            raise FontTimeoutError("Remote font request timed out.") from exc
        except UnsafeFontURLError:
            raise
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            raise FontFetchError("Remote font could not be retrieved.") from exc

        try:
            status = response.status
            headers = {key.lower(): value for key, value in response.headers.items()}
            if status in {301, 302, 303, 307, 308}:
                location = response.headers.get("Location")
                response.read()
                if not location:
                    raise FontFetchError("Redirect response missing Location.")
                current = urljoin(current, location)
                validate_remote_font_url(current)
                continue
            if status != 200:
                raise FontFetchError(f"Remote font returned HTTP {status}.")
            body = _read_limited(response, max_size)
        finally:
            conn.close()

        suffix = ".woff2"
        lower_url = current.lower()
        for ext in (".woff2", ".woff", ".otf", ".ttf"):
            if lower_url.endswith(ext):
                suffix = ext
                break

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(body)
            return temp.name, headers

    raise UnsafeFontURLError(f"Too many redirects (max {MAX_REDIRECTS}).")
