# -*- coding: utf-8 -*-
"""Read dkwk.conf from $SYSCONFDIR.

The file is rc-style: one ``key=value`` per line, ``#`` for
full-line comments, blank lines ignored.  Whitespace around the
key and value is stripped.  Values are not quoted and not
interpolated.

Eventually this could be replaced by python-dotenv (which would
also let us drop into ``os.environ``); for now we just split on
``=`` ourselves so we don't pull in a dependency for ~20 lines
of parsing.
"""

import os

from .config import SYSCONFDIR


CONF_NAME = 'dkwk.conf'

KNOWN_KEYS = (
    'git_remote_uri',
    'git_remote_ssh_publickey',
    'git_remote_ssh_secretkey',
    'git_remote_ssh_passphrase',
)

# Default = absent.  Callers that depend on these (e.g. the push
# background task) should check for None and decline to act.
git_remote_uri            = None
git_remote_ssh_publickey  = None
git_remote_ssh_secretkey  = None
git_remote_ssh_passphrase = None


def load(path=None):
    """
    (Re-)read dkwk.conf and update this module's globals for any
    KNOWN_KEYS that appear.  Returns the full parsed dict
    (including unknown keys, in case a caller wants them).

    A missing file is treated as empty -- not an error, since the
    push task is opt-in.  Syntax errors raise ValueError.
    """
    if path is None:
        path = os.path.join(SYSCONFDIR, CONF_NAME)

    data = parse_env(path)

    g = globals()
    for key in KNOWN_KEYS:
        if key in data:
            g[key] = data[key]
    return data


def parse_env(path):
    out = {}
    try:
        f = open(path, encoding='utf-8')
    except FileNotFoundError:
        return out
    with f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                raise ValueError(
                    f"{path}:{lineno}: missing '=' in line: {raw!r}")
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            if not key:
                raise ValueError(f"{path}:{lineno}: empty key")
            out[key] = value
    return out


# Populate the module attributes once at import time.  Callers
# that want to re-read after a config change can call load()
# again explicitly.
load()
