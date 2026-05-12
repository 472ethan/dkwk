# -*- coding: utf-8 -*-
"""URI classification and normalization helpers.

Right now this is just SSH detection for the push background
task, but the module is the natural home for any future
URI-shaped parsing we end up needing (HTTPS-with-credentials,
git protocol, file://, ...).
"""

import re
import urllib.parse


# RFC 3986 Sect 3.1
# scheme      = ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )
GIT_PROTO = re.compile(r'git\+([a-zA-Z][a-zA-Z0-9+-.]*://)', flags=re.IGNORECASE)
# The dots are greedy enough in this case, $ shouldn't be necessary...
SCP_REGEX = re.compile(r'(.+@.+?):(.*)', flags=re.DOTALL)

def parse_git_remote(location):
    """
    Return a canonical Git remote location.

    - ``ssh://...``        -> returned as-is
    - ``git+ssh://...``    -> ``git+`` prefix stripped
    - scp-style specifier
      ``user@host:/path``       -> ``ssh://user@host/path``
      ``user@host:~name/path``  -> ``ssh://user@host/~name/path``
      ``user@host:path``        -> ``ssh://user@host/~/path``
      (git's connect.c strips the leading ``/`` of an
      ``ssh://`` URI when the path's second char is ``~``, so
      ``/~name/path`` survives transport as ``~name/path``.
      For bare relative paths we prepend ``/~/`` as a
      convention to get the same home-relative wire path.)

    Raise ValueError on malformed scp-specifiers and URIs alike.

    BUG: an SCP string may not have a "://" anywhere.
    This is a dirty solution since schemes are clearly
    restricted to a subset of ASCII characters.
    """
    if not location:
        raise ValueError('empty URI')
    try_git = GIT_PROTO.match(location)
    if try_git:
        norm = f"{try_git.group(1)}{location[try_git.end():]}"
    else:
        try_scp = '://' not in location and SCP_REGEX.match(location)
        if try_scp:
            host, path = try_scp.groups()
            if path.startswith('/'):
                pass                    # absolute, leave as /path
            elif path.startswith('~'):
                path = f"/{path}"       # /~name/path -- git strips '/'
            else:
                path = f"/~/{path}"     # bare -- home-relative convention
            norm = f"ssh://{host}{path}"
        else:
            norm = location
    uri = urllib.parse.urlsplit(norm)
    return uri
