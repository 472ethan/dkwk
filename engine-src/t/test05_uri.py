# -*- coding: utf-8 -*-
"""Tests for dkwk.uri."""

import unittest

from dkwk.uri import parse_git_remote as n


class TestRemoteLoc(unittest.TestCase):
    """URI classification for git_remote_uri.

    Not critical for operation -- a misclassified URI just means
    we fail to wire GIT_SSH_COMMAND and git push errors out --
    but enough else hangs off this that regressions are worth
    catching.
    """

    def test_ssh_uri_passthrough(self):
        r = n('ssh://git@host/path')
        self.assertEqual(r.scheme, 'ssh')
        self.assertEqual(r.netloc, 'git@host')
        self.assertEqual(r.path, '/path')
        self.assertIsNone(r.port)

    def test_ssh_uri_with_port(self):
        r = n('ssh://git@host:2222/path')
        self.assertEqual(r.scheme, 'ssh')
        self.assertEqual(r.netloc, 'git@host:2222')
        self.assertEqual(r.path, '/path')
        self.assertIsInstance(r.port, int)
        self.assertEqual(r.port, 2222)

    def test_git_plus_ssh_stripped(self):
        r = n('git+ssh://git@host/path')
        self.assertEqual(r.scheme, 'ssh')
        self.assertEqual(r.netloc, 'git@host')
        self.assertEqual(r.path, '/path')
        self.assertIsNone(r.port)

    def test_scp_style_home_relative(self):
        # 'user@host:path'  ->  ssh://user@host/~/path
        r = n('git@host:foo/bar.git')
        self.assertEqual(r.scheme, 'ssh')
        self.assertEqual(r.netloc, 'git@host')
        self.assertEqual(r.path, '/~/foo/bar.git')
        self.assertIsNone(r.port)

    def test_scp_style_absolute(self):
        # 'user@host:/path'  ->  ssh://user@host/path
        # (no /~/ marker -- leading slash means real absolute path)
        r = n('git@host:/srv/repo.git')
        self.assertEqual(r.scheme, 'ssh')
        self.assertEqual(r.netloc, 'git@host')
        self.assertEqual(r.path, '/srv/repo.git')
        self.assertIsNone(r.port)

    def test_malformed_raises(self):
        # Per docstring: ValueError on malformed inputs.
        with self.assertRaises(ValueError):
            n('')  # empty
