"""Reverse proxy header utilities."""

__all__ = ['peer_address']

import fastapi


def peer_address(request: fastapi.Request) -> str:
    """
    Return the visitor's IP address, checking in order:
      1. Forwarded (RFC 7239) — first for= node
      2. X-Forwarded-For — leftmost entry
      3. X-Real-IP
      4. request.client.host (raw TCP peer, typically the proxy itself)
    Raises ValueError if no address can be determined.
    """
    forwarded = request.headers.get('Forwarded')
    if forwarded:
        ip = parse_forwarded(forwarded)
        if ip:
            return ip

    xff = request.headers.get('X-Forwarded-For')
    if xff:
        ip = xff.split(',')[0].strip()
        if ip:
            return ip

    xri = request.headers.get('X-Real-IP')
    if xri:
        ip = xri.strip()
        if ip:
            return ip

    if request.client:
        return request.client.host

    raise ValueError("peer address unavailable: no Forwarded/X-Forwarded-For/X-Real-IP header and no client socket")


def parse_forwarded(header: str) -> str | None:
    """
    Pull the IP out of the first for= directive in a Forwarded header.
    Returns None for unknown/obfuscated identifiers or parse failures.
    """
    first = header.split(',')[0]
    for directive in first.split(';'):
        directive = directive.strip()
        if directive.lower().startswith('for='):
            return extract_node_ip(directive[4:])
    return None


def extract_node_ip(node: str) -> str | None:
    """
    Parse a Forwarded for= node value into a bare IP string.
    Handles quoted strings, IPv6 brackets, and optional port suffixes.
    Returns None for 'unknown' or _obfuscated identifiers.
    """
    if len(node) >= 2 and node[0] == '"' and node[-1] == '"':
        node = node[1:-1]

    if not node or node.lower() == 'unknown' or node.startswith('_'):
        return None

    # IPv6: [::1] or [::1]:port
    if node.startswith('['):
        end = node.find(']')
        return node[1:end] if end != -1 else None

    # IPv4 with optional port: 1.2.3.4 or 1.2.3.4:5678
    if ':' in node:
        return node.rsplit(':', 1)[0]

    return node or None
