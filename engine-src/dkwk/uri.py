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
GIT_PROTO = re.compile(r'git\+([a-zA-Z][a-zA-Z0-9+-.]*://)')
# The dots are greedy enough in this case, $ shouldn't be necessary...
SCP_REGEX = re.compile(r'(.+@.+?):(.*)', flags=re.DOTALL)

def parse_git_remote(location):
    """
    Return a canonical Git remote location.

    - ``ssh://...``        -> returned as-is
    - ``git+ssh://...``    -> ``git+`` prefix stripped
    - scp-style specifier
      ``user@host:/path`` -> ``ssh://user@host/path``
      ``user@host:path`` -> ``ssh://user@host/~/path``
      (the ``/~/`` marker preserves the home-relative path
      semantics of scp-style URIs; git itself understands it,
      and a consumer reconstructing the scp form just drops the
      leading slash from ``/~/path``)

    Raise ValueError on malformed scp-specifiers and URIs alike.
    """
    if not location:
        raise ValueError('empty URI')
    try_git = GIT_PROTO.match(location)
    if try_git:
        norm = f"{try_git.group(1)}{location[try_git.end():]}"
    else:
        try_scp = SCP_REGEX.match(location)
        if try_scp:
            host, path = try_scp.groups()
            if not path.startswith('/'):
                path = f"/~/{path}"
            norm = f"ssh://{host}{path}"
        else:
            norm = location
    uri = urllib.parse.urlsplit(norm)
    return uri
