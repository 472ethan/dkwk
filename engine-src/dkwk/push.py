# -*- coding: utf-8 -*-
"""Background Git push using native OpenSSH via ``git push``.

We shell out to git/ssh rather than pygit2.Remote.push because
pygit2/libssh2 doesn't expose known_hosts handling.  OpenSSH
does (``StrictHostKeyChecking=accept-new``), which gives us TOFU
on the first push and rejection on any host-key change.

When the configured key has a passphrase, we feed it to ssh via
SSH_ASKPASS pointing at a shell wrapper that ``cat``s a FIFO in
a private tempdir.  The passphrase never lands in a regular
file -- only the running ssh sees it on its way out of the pipe.
"""

import logging
import os
import shlex
import subprocess
import tempfile
import threading

from . import conf
from .uri import parse_git_remote

# Auto-load conf so callers don't have to.  Tests that need to
# override should patch dkwk.conf.CONF_PATH and re-call
# conf.load() before invoking push().
conf.load()

log = logging.getLogger(__name__)

PUSH_TIMEOUT = 60  # seconds


def push(repo_path, branch):
    """Push ``refs/heads/<branch>`` to ``conf.git_remote_uri``.

    No-op when no remote URI is configured (local mode).  All
    failures are logged and swallowed; the HTTP response was
    already sent by the time this background task runs.
    """
    uri = conf.git_remote_uri
    if not uri:
        return  # local mode
    priv = conf.git_remote_ssh_secretkey
    passwd = conf.git_remote_ssh_passphrase or ''

    uri = parse_git_remote(uri)
    if uri.scheme == 'ssh' and not priv:
        log.error("ssh remote %s but git_remote_ssh_secretkey is not set",
                  uri)
        return

    cmd = ['git', '-C', repo_path, 'push', uri,
           f'refs/heads/{branch}']
    env = os.environ.copy()

    if not is_ssh:
        run(cmd, env, uri, branch, feeder=None)
        return

    env['GIT_SSH_COMMAND'] = (
        f"ssh -i {shlex.quote(priv)}"
        f" -o BatchMode=yes"
        f" -o StrictHostKeyChecking=accept-new"
        f" -o IdentitiesOnly=yes"
    )
    with tempfile.TemporaryDirectory(prefix='dkwk-push-') as tmpdir:
        feeder = wire_askpass(env, tmpdir, passwd)
        try:
            run(cmd, env, uri, branch, feeder=feeder)
        finally:
            feeder.unblock()


def run(cmd, env, uri, branch, feeder):
    proc = subprocess.Popen(
        cmd, env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        _, stderr = proc.communicate(timeout=PUSH_TIMEOUT)
    except subprocess.TimeoutExpired:
        proc.kill()
        _, stderr = proc.communicate()
        log.error("git push to %s timed out", uri)
        return
    if proc.returncode != 0:
        log.error("git push to %s failed (%d): %s",
                  uri, proc.returncode,
                  stderr.decode(errors='replace').rstrip())
        return
    log.info("pushed %s to %s", branch, uri)


def wire_askpass(env, tmpdir, passphrase):
    """Set SSH_ASKPASS env in ``env`` and return a Feeder."""
    fifo = os.path.join(tmpdir, 'pass.fifo')
    askpass = os.path.join(tmpdir, 'askpass')
    os.mkfifo(fifo, 0o600)
    with open(askpass, 'w', encoding='ascii') as fp:
        fp.write(f'#!/bin/sh\nexec cat {shlex.quote(fifo)}\n')
    os.chmod(askpass, 0o700)
    env['SSH_ASKPASS'] = askpass
    env['SSH_ASKPASS_REQUIRE'] = 'force'  # OpenSSH 8.4+
    env['DISPLAY'] = ''                   # belt-and-braces for older sshd
    return Feeder(fifo, passphrase)


class Feeder:
    """Owns the writer side of the askpass FIFO."""

    def __init__(self, fifo, passphrase):
        self.fifo = fifo
        self.thread = threading.Thread(target=self.write,
                                       args=(passphrase,),
                                       daemon=True)
        self.thread.start()

    def write(self, passphrase):
        # open() on a FIFO blocks until a reader appears (here:
        # the askpass `cat`).  We write the passphrase then close.
        try:
            with open(self.fifo, 'wb') as fp:
                fp.write((passphrase + '\n').encode('utf-8'))
        except OSError as e:
            log.warning("askpass FIFO write failed: %s", e)

    def unblock(self):
        # If ssh never invoked askpass (e.g. the key turned out
        # not to be encrypted), the writer is still blocked on
        # open().  Open the read-side ourselves once to release
        # it, so the thread can finish before TemporaryDirectory
        # tears the FIFO out from under it.
        try:
            fd = os.open(self.fifo, os.O_RDONLY | os.O_NONBLOCK)
            try:
                os.read(fd, 4096)
            except OSError:
                pass
            os.close(fd)
        except OSError:
            pass
        self.thread.join(timeout=1)
