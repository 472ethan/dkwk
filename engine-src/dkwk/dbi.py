"""Database interface.  We use Git for content storage."""

import os
import pygit2

from . import git as git


__all__ = [
    'Repository',
]


class MovedError(RuntimeError):
    """Incompatible heads."""

    # *_up parameters for upstream (old commit)
    # *_dn parameters for downstream (new commit)
    __slots__ = ('name', 'id_up', 'id_dn', 'co_up', 'co_dn')

    def __init__(self, name, id_up, id_dn=None, co_up=0, co_dn=0):
        self.name = name
        self.id_up = id_up
        self.id_dn = id_dn
        self.co_up = co_up
        self.co_dn = co_dn

    def __str__(self):
        buf = [f"{self.name!r}: "]
        if not self.id_dn:
            buf.append(f"{self.id_up} deleted")
        else:
            buf.append(f"{self.id_up} -> {self.id_dn}")
            buf.append(f" ({self.co_up} commit{'s' * (self.co_up != 1)} dropped, ")
            buf.append(f" {self.co_dn} commit{'s' * (self.co_dn != 1)} added)")
        return ''.join(buf)


class Repository:
    """Connection to Git object database."""

    __slots__ = ('repo', 'name', 'head', 'txn')

    def __init__(self, path, branch):
        self.repo = pygit2.Repository(path)
        self.name = branch
        # Lock ref
        try:
            self.head = self.repo.revparse_single(f"refs/heads/{branch}")
        except KeyError:
            self.head = None
        # Instead of keeping a whole index, we keep just
        # the list of subtrees we changed.  In our case,
        # it'd be the "wiki" subtree.
        #
        # ("txn" short for transactions.)
        self.txn = {}

    def join(self, subtree):
        tree = subtree.save()
        # TreeBuilder can only make use of the oid itself.
        self.txn[subtree.path] = tree.id

    def wiki(self):
        return WikiTree(self.repo, self.head)

    # The committer field is provided for unit testing.
    def commit(self, author, message, committer=None):
        if not self.txn:
            return self.head.id
        if self.head:
            parents = [self.head.id]
            oldtree = self.head.peel(pygit2.Tree)
            index = self.repo.TreeBuilder(oldtree)
        else:
            parents = []
            index = self.repo.TreeBuilder()
        for path, node in self.txn.items():
            index.insert(path, node, pygit2.GIT_FILEMODE_TREE)
        tree = index.write()
        oid = git_commit(self.repo, f"refs/heads/{self.name}",
            tree, parents, author, committer, message)
        self.head = self.repo[oid]
        return oid

    def __repr__(self):
        return f"<{type(self).__qualname__} at {self.head}>"


def git_commit(repo, name, *args, **kwds):
    """
    git.commit technically only creates the commit.
    This does the harder part of "locking" the refs
    and updating them.

    This is stolen from minigit.py.
    """
    myname = f"{__name__} git_commit"
    oid = git.commit(repo, *args, **kwds)
    # Round-trip the commit; we pray for the best?
    message = repo[oid].message

    try:
        oldoid = repo.lookup_reference(name).resolve().target
    except KeyError:
        oldoid = None

    # For good interpolation: prepend the colon only
    # if a commit message was given.
    try:
        (line,) = message.splitlines()
    except ValueError:
        subj = ""
    else:
        subj = f": {line}"

    # Unlike minigit.py, I am not concerned about reproducibility;
    # just log with whatever identity it likes. :)

    if oldoid:
        ref = repo.lookup_reference(name)
        newoid = ref.resolve().target
        if newoid != oldoid:
            raise ValueError(f"{name} has changed: into {newoid}, was {oldoid}")
        ref.set_target(oid, message=f"{myname} (initial){subj}")
        return oid
    else:
        try:
            newoid = repo.lookup_reference(name).resolve().target
        except KeyError:
            pass
        else:
            raise ValueError(f"{name} has changed: into {newoid}, was unborn")
        repo.create_reference(name, oid)
        return oid


class Tree:
    """Direct Git tree interface."""

    __slots__ = ('repo', 'tree', 'index')

    def __init_subclass__(cls, path):
        cls.path = path

    # We are going to cheat loading a bit.  Essentially,
    # if we are performing a purely read operation (where
    # most of a Wiki's life is spent), the "cache" is good
    # enough -- in which case we just consult the tree.
    #
    # Note that this also means that the "index" has no
    # meaningful interpretation when "tree" is set.

    def __init__(self, repo, head):
        self.repo = repo
        # We accept a tree-ish
        root = head.peel(pygit2.Tree)
        try:
            self.tree = root / self.path
        except KeyError:
            # Bummer; we'll make a new tree...
            # (though we don't have to be loud about it.)
            self.tree = None
        self.index = None

    def load(self):
        index = self.index
        if not index:
            index = pygit2.Index()
            store = self.tree
            if store:
                index.read_tree(store)
            self.index = index
        return index

    def save(self):
        if not self.tree:
            tree = self.index.write_tree(self.repo)
            self.tree = self.repo[tree]
        return self.tree

    def read(self, path):
        if self.tree:
            blob = self.tree[path].id
        elif self.index:
            blob = self.index[path].id
        else:
            raise KeyError(path)
        return self.repo[blob].data

    def write(self, path, data):
        blob = self.repo.create_blob(data)
        index = self.load()
        cache = pygit2.IndexEntry(path, blob, pygit2.GIT_FILEMODE_BLOB)
        index.add(cache)
        self.tree = None  # invalidate

    def delete(self, path):
        index = self.load()
        index.remove(path)


class WikiTree(Tree, path='wiki'):
    """Database model for the 'wiki' subtree."""
