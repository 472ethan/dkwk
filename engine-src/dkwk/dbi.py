"""Database interface.  We use Git for content storage."""

import os
import pygit2


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

    __slots__ = ('repo', 'name', 'head')

    def __init__(self, path, branch):
        self.repo = pygit2.Repository(path)
        self.name = branch
        # Lock ref
        try:
            self.head = self.repo.revparse_single(f"refs/heads/{branch}")
        except KeyError:
            self.head = None

    def join(self, subtree):
        subtree.save()

    def wiki(self):
        return WikiTree(self.repo, self.head)

    def __repr__(self):
        return f"<{type(self).__qualname__} at {self.head}>"


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
