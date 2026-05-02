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

    def test_savepath(self):
        rebo = pygit2.init_repository(self.ROOT,
            initial_head='refs/heads/master', bare=True)
        index = pygit2.Index()
        blob = rebo.create_blob(b'= welcome! =\n')
        index.add(pygit2.IndexEntry('wiki/index.txt', blob, pygit2.GIT_FILEMODE_BLOB))
        tree = index.write_tree(rebo)
        HEAD = git_commit(rebo, 'refs/heads/master', tree)
        repo = dbi.Repository(self.ROOT, 'master')
        wiki = repo.wiki()
        wiki.write('guide/index.txt', b'= Guide to the Galaxy =\n')
        self.assertEqual(wiki.read('guide/index.txt'), b'= Guide to the Galaxy =\n')
        self.assertEqual(wiki.read('index.txt'), b'= welcome! =\n')
        wiki.save()
        self.assertEqual(wiki.read('guide/index.txt'), b'= Guide to the Galaxy =\n')
        self.assertEqual(wiki.read('index.txt'), b'= welcome! =\n')

    def test_committree(self):
        rebo = pygit2.init_repository(self.ROOT,
            initial_head='refs/heads/master', bare=True)
        index = pygit2.Index()
        blob = rebo.create_blob(b'= welcome! =\n')
        index.add(pygit2.IndexEntry('wiki/index.txt', blob, pygit2.GIT_FILEMODE_BLOB))
        blob = rebo.create_blob(b'print("Hello world")\n')
        index.add(pygit2.IndexEntry('engine-src/hello.py', blob, pygit2.GIT_FILEMODE_BLOB))
        tree = index.write_tree(rebo)
        HEAD = git_commit(rebo, 'refs/heads/master', tree)
        repo = dbi.Repository(self.ROOT, 'master')
        wiki = repo.wiki()
        wiki.write('guide.txt', b'= guide =\n')
        wiki.save()
        repo.join(wiki)
        repo.commit(
            # In practice, the committer is left to None,
            # so the daemon identity as well as system clock
            # can be used.
            author='127.0.0.1 <www-data@engine.cs472.endfind.me> 1777661692 -0000',
            committer='HTTP Daemon <www-data@engine.cs472.endfind.me> 1777661692 -0000',
            message="POST /api/post?f=guide/index.txt\n",
        )
        self.assertEqual(rebo.revparse_single('refs/heads/master'), repo.head)
        self.assertEqual(repo.head.author.name, '127.0.0.1')
        self.assertEqual(repo.head.author.email, 'www-data@engine.cs472.endfind.me')
        self.assertEqual(repo.head.author.time, 1777661692)
        self.assertEqual(repo.head.author.offset, 0)
        self.assertEqual(repo.head.committer.name, 'HTTP Daemon')
        self.assertEqual(repo.head.committer.email, 'www-data@engine.cs472.endfind.me')
        self.assertEqual(repo.head.committer.time, 1777661692)
        self.assertEqual(repo.head.committer.offset, 0)
        self.assertEqual(repo.head.message, "POST /api/post?f=guide/index.txt\n")
        self.assertEqual(repo.head.tree['engine-src/hello.py'].read_raw(), b'print("Hello world")\n')
