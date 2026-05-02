"""Access-control list."""

__all__ = ['check_path', 'can_read', 'can_write']

import re

_SAFE = re.compile(r'^[A-Za-z0-9_\-][A-Za-z0-9_\-/]*$')


def check_path(name):
    """Return the validated page name, or raise ValueError."""
    if not name:
        raise ValueError("empty page name")
    if '..' in name.split('/'):
        raise ValueError(f"path traversal in name: {name!r}")
    if not _SAFE.match(name):
        raise ValueError(f"invalid characters in name: {name!r}")
    return name


def can_read(name):
    """All pages are readable."""
    return True


def can_write(name):
    """Only the Guestbook/ subtree is writable."""
    return name.startswith('Guestbook/')
