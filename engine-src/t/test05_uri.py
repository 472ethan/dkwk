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

    def test_scp_style_tilde_anonymous(self):
        # 'user@host:~/path'  ->  ssh://user@host/~/path
        # Single leading '/' is enough -- git's connect.c strips
        # it on the wire when path[1] == '~', so wire path is
        # ~/path.  (Real path that resolves to pub/lib/perl5/
        # Sort-Search.git on the RPi git shell.)
        r = n('git@RPi-4B:~/lib/perl5/Sort-Search.git')
        self.assertEqual(r.scheme, 'ssh')
        self.assertEqual(r.netloc, 'git@RPi-4B')
        self.assertEqual(r.path, '/~/lib/perl5/Sort-Search.git')
        self.assertIsNone(r.port)

    def test_scp_style_tilde_user_prefix(self):
        # 'user@host:~name/path'  ->  ssh://user@host/~name/path
        # Same single-slash rule -- wire path is ~name/path,
        # NOT /~/~name/path (which is what an unconditional
        # /~/ prefix would produce).
        r = n('git@RPi-4B:~ethan/ics/uwisc/cs472/p2-site.git')
        self.assertEqual(r.scheme, 'ssh')
        self.assertEqual(r.netloc, 'git@RPi-4B')
        self.assertEqual(r.path, '/~ethan/ics/uwisc/cs472/p2-site.git')
        self.assertIsNone(r.port)

    def test_malformed_raises(self):
        # Per docstring: ValueError on malformed inputs.
        with self.assertRaises(ValueError):
            n('')  # empty

    # --- native local-path passthrough ------------------------
    # git's "local transport" wants the bare path, not a
    # file:// URI.  We rely on urlsplit being lax: it splits on
    # delimiters but never percent-encodes, so .geturl() round-
    # trips the original string verbatim.

    def test_local_path_with_spaces(self):
        r = n('/home/user/my repo.git')
        self.assertEqual(r.scheme, '')
        self.assertEqual(r.geturl(), '/home/user/my repo.git')
        r = n('./my repo.git')
        self.assertEqual(r.geturl(), './my repo.git')

    def test_local_path_fragment_and_query_delimiters(self):
        # '#' and '?' get peeled off into fragment/query, so
        # parsed.path is truncated -- but .geturl() reassembles
        # the original.  We only consume .geturl() downstream,
        # so the round-trip is what matters.
        r = n('/path/with#hash/repo.git')
        self.assertEqual(r.geturl(), '/path/with#hash/repo.git')
        r = n('/path/with?q=1/repo.git')
        self.assertEqual(r.geturl(), '/path/with?q=1/repo.git')

    def test_local_path_preserves_existing_percent_encoding(self):
        # We must not double-encode (or decode) percent escapes.
        r = n('/path/with%20already/repo.git')
        self.assertEqual(r.geturl(), '/path/with%20already/repo.git')

    def test_local_path_preserves_invalid_percent_sequences(self):
        # urlsplit/geturl don't validate percent escapes -- they
        # just shuffle bytes -- so malformed '%' bytes that a
        # strict decoder would reject still round-trip verbatim.
        # Important because the filesystem genuinely allows any
        # byte in a filename, '%' included.
        for raw in [
            '/path/with%1g/repo.git',   # non-hex second nibble
            '/path/with%g0/repo.git',   # non-hex first nibble
            '/path/with%ZZ/repo.git',   # both nibbles bad
            '/path/with%2/repo.git',    # truncated escape
            '/path/with%/repo.git',     # bare '%'
            '/path/with%%20/repo.git',  # literal '%' before a valid escape
            '/100%/repo.git',           # trailing '%' on a path segment
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(n(raw).geturl(), raw)

    def test_non_ascii_preserved(self):
        # Local paths carry non-ASCII through unchanged.
        self.assertEqual(n('/home/user/résumé.git').geturl(),
                         '/home/user/résumé.git')
        self.assertEqual(n('/home/user/プロジェクト.git').geturl(),
                         '/home/user/プロジェクト.git')
        self.assertEqual(n('/home/user/日本語 with spaces.git').geturl(),
                         '/home/user/日本語 with spaces.git')
        # scp-style: non-ASCII in user/host propagates into the
        # synthesized ssh:// netloc.
        self.assertEqual(n('git@résumé.example:repo.git').geturl(),
                         'ssh://git@résumé.example/~/repo.git')
