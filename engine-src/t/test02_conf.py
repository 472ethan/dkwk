# -*- coding: utf-8 -*-
"""Tests for dkwk.conf."""

import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

# dkwk.config is generated from config.py.in at install time and
# doesn't exist in the source tree, so we stub it before
# importing dkwk.conf.
_stub = types.ModuleType('dkwk.config')
_stub.SYSCONFDIR = '/nonexistent'


@patch.dict(sys.modules, {'dkwk.config': _stub})
class TestConf(unittest.TestCase):
    def test_parse_env(self):
        import dkwk.conf as conf
        with tempfile.NamedTemporaryFile(
                'w', suffix='.conf', delete=False,
                encoding='utf-8') as f:
            f.write(
                "# sample dkwk.conf\n"
                "\n"
                "git_remote_uri=ssh://git@example.invalid/wiki.git\n"
                "git_remote_ssh_publickey = /etc/dkwk/id_ed25519.pub\n"
                "git_remote_ssh_secretkey=/etc/dkwk/id_ed25519\n"
                "git_remote_ssh_passphrase=\n"
                "ignored_key=whatever\n"
            )
            path = f.name
        try:
            data = conf.parse_env(path)
        finally:
            os.unlink(path)
        self.assertEqual(data['git_remote_uri'],
                         'ssh://git@example.invalid/wiki.git')
        self.assertEqual(data['git_remote_ssh_publickey'],
                         '/etc/dkwk/id_ed25519.pub')
        self.assertEqual(data['git_remote_ssh_secretkey'],
                         '/etc/dkwk/id_ed25519')
        self.assertEqual(data['git_remote_ssh_passphrase'], '')
        self.assertEqual(data['ignored_key'], 'whatever')
