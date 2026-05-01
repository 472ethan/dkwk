import unittest
import os
import tempfile

import pygit2

import dkwk.dbi as dbi
from minigit import *


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

    def test_somerepo(self):
        rebo = pygit2.init_repository(self.ROOT,
            initial_head='refs/heads/master', bare=True)
        index = pygit2.Index()
        blob = rebo.create_blob(b'= welcome! =\n')
        index.add(pygit2.IndexEntry('wiki/index.txt', blob, pygit2.GIT_FILEMODE_BLOB))
        tree = index.write_tree(rebo)
        HEAD = git_commit(rebo, 'refs/heads/master', tree)
        repo = dbi.Repository(self.ROOT, 'master')
        self.assertEqual(repo.head.id, HEAD)

    def test_readpath(self):
        rebo = pygit2.init_repository(self.ROOT,
            initial_head='refs/heads/master', bare=True)
        index = pygit2.Index()
        blob = rebo.create_blob(b'= welcome! =\n')
        index.add(pygit2.IndexEntry('wiki/index.txt', blob, pygit2.GIT_FILEMODE_BLOB))
        tree = index.write_tree(rebo)
        HEAD = git_commit(rebo, 'refs/heads/master', tree)
        repo = dbi.Repository(self.ROOT, 'master')
        wiki = repo.wiki()
        self.assertEqual(wiki.read('index.txt'), b'= welcome! =\n')
        with self.assertRaises(KeyError):
            wiki.read('marketing.txt')
