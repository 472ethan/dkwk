import datetime
import pygit2

import dkwk as dinky
from dkwk.git import *  # (mkgitid)

__all__ = [
    'git_commit_tree',
]

IDENT_NAME = __name__
IDENT_EMAIL = ''


def git_commit(repo, name, tree, *, time=None, message=''):
    """
    Make a commit at reference named `name'.

    Return pygit2.Oid of the old commit and the new commit.
    The old commit is None if the reference is unborn.
    """
    myname = f"{__name__} git_commit"
    try:
        ref = repo.lookup_reference(name)
    except KeyError:
        parents = []
    else:
        if ref.type is not pygit2.enums.ReferenceType.SYMBOLIC:
            parents = [ref.target]
        else:
            name = ref.target
            try:
                reft = ref.resolve()
            except KeyError:
                parents = []
            else:
                parents = [reft.target]

    author = mkgitid(IDENT_NAME, IDENT_EMAIL, time)
    committer = mkgitid(IDENT_NAME, IDENT_EMAIL, time)
    oid = dinky.git.commit(repo, tree, parents, author, committer, message)

    # For good interpolation: prepend the colon only
    # if a commit message was given.
    try:
        (line,) = message.splitlines()
    except ValueError:
        subj = ""
    else:
        subj = f": {line}"

    # It's hard to enforce identity on reflogs... I'll try my best here.
    ident = pygit2.Signature(IDENT_NAME, IDENT_EMAIL, offset=0)

    if parents:
        (oldoid,) = parents[0]
        ref = repo.lookup_reference(name)
        newoid = ref.resolve().target
        if newoid != oldoid:
            raise ValueError(f"{name} has changed: {newoid}, was {oldoid}")
        ref.set_target(oid, message=f"{myname} (initial){subj}")
    else:
        try:
            newoid = repo.lookup_reference(name).resolve().target
        except KeyError:
            pass
        else:
            raise ValueError(f"{name} has changed: {newoid}, was unborn")
        # Setting identity is (very much) hopeless here; at least, not
        # in a way that isn't destructive.  We don't have a way to fix
        # this and this is an upstream bug.
        repo.create_reference(name, oid)
