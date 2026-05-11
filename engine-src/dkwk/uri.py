# -*- coding: utf-8 -*-
"""URI classification and normalization helpers.

Right now this is just SSH detection for the push background
task, but the module is the natural home for any future
URI-shaped parsing we end up needing (HTTPS-with-credentials,
git protocol, file://, ...).
"""

import re

SCP_RE = re.compile(r'^(.+@.+?):(.*)$')


def normalize_ssh_uri(uri):
    """
    Return a canonical ``ssh://...`` URI if ``uri`` is SSH-y,
    else ``None``.

    - ``ssh://...``        -> returned as-is
    - ``git+ssh://...``    -> ``git+`` prefix stripped
    - scp-style ``user@host:path`` -> ``ssh://user@host/~/path``
      (the ``/~/`` marker preserves the home-relative path
      semantics of scp-style URIs; git itself understands it,
      and a consumer reconstructing the scp form just drops the
      leading slash from ``/~/path``)
    - any other scheme (http, https, git, file, ...) -> ``None``
    - plain local paths -> ``None``
    """
    if uri.startswith('git+ssh://'):
        return uri[len('git+'):]
    if uri.startswith('ssh://'):
        return uri
    if '://' in uri:
        return None  # other scheme
    m = SCP_RE.match(uri)
    if m:
        return f'ssh://{m.group(1)}/~/{m.group(2)}'
    return None
