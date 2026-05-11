# -*- coding: utf-8 -*-
"""Tests for dkwk.uri."""

import unittest

from dkwk.uri import normalize_ssh_uri as n


class TestRemoteLoc(unittest.TestCase):
    """URI classification for git_remote_uri.

    Not critical for operation -- a misclassified URI just means
    we fail to wire GIT_SSH_COMMAND and git push errors out --
    but enough else hangs off this that regressions are worth
    catching.
    """

    def test_ssh_uri_passthrough(self):
        self.assertEqual(n('ssh://git@host/path'),
                         'ssh://git@host/path')
        self.assertEqual(n('ssh://git@host:2222/path'),
                         'ssh://git@host:2222/path')

    def test_git_plus_ssh_stripped(self):
        self.assertEqual(n('git+ssh://git@host/path'),
                         'ssh://git@host/path')

    def test_scp_style_translated(self):
        # Home-relative marker is /~/, which git itself
        # understands.
        self.assertEqual(n('git@host:foo/bar.git'),
                         'ssh://git@host/~/foo/bar.git')
        self.assertEqual(n('git@host:bar.git'),
                         'ssh://git@host/~/bar.git')

    def test_non_ssh_returns_none(self):
        self.assertIsNone(n('https://host/path'))
        # Userinfo-with-port URLs must not be mistaken for scp.
        self.assertIsNone(n('https://user@host:443/path'))
        self.assertIsNone(n('git+https://user@host/path'))
        self.assertIsNone(n('/local/path'))
        self.assertIsNone(n('plain.host:path'))  # no '@', not scp
