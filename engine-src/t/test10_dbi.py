import unittest
import os
import tempfile

import pygit2

import dkwk.dbi as dbi


class TestDbi_Repo(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.temp = tempfile.TemporaryDirectory()
        self.ROOT = os.path.join(self.temp.name, 'wiki.git')
        pygit2.init_repository(self.ROOT)

    def tearDown(self):
        self.temp.cleanup()
        super().tearDown()


class TestDbi_Tree(TestDbi_Repo):
    """Base tests for libgit2 ops."""

    def test_emptyrepo(self):
        repo = dbi.Repository(self.ROOT, 'main')
        self.assertIs(repo.head, None)
