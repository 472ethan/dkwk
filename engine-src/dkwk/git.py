"""Low-level Git compat interface."""

__all__ = [
    'mkgitid',
]

import datetime
import pygit2

UTC = datetime.timezone.utc
# Anything naive here is UTC.
EPOCH = datetime.datetime(1970, 1, 1)
SECOND = datetime.timedelta(seconds=1)
MINUTE = datetime.timedelta(minutes=1)


def datetime_is_naive(d):
    """
    Return if a datetime.datetime instance is naive.
    """
    # Per <https://docs.python.org/3/library/datetime.html#determining-if-an-object-is-aware-or-naive>:
    # A datetime object d is aware if both of the following hold:
    #   * d.tzinfo is not None
    #   * d.tzinfo.utcoffset(d) does not return None
    # Otherwise, d is naive.
    #
    # It's naive if either one returns None.
    return d.tzinfo is None or d.tzinfo.utcoffset(d) is None


def mkgitid(name, mail, time=None):
    """
    Make Git identity.  What you pass in roughly becomes:

        "${name} <${mail}> ${time.strftime( '%s %z ) }"

    except naive time is treated as UTC and formatted as -0000.

    If time is omitted, use 0 -0000 (1970-01-01T00:00:00Z).
    """
    # Source: fsck_commit, fsck_ident in fsck.c
    # I'm looking (loosely) at git.git:master, but the idea
    # should hold in general.

    # This first bit is our validation though:
    if time is None:
        time = EPOCH
    elif not isinstance(time, datetime.datetime):
        raise ValueError(f"time should be a datetime.datetime "
                         f"instance, not {type(time).__name__}")

    # NUL that appears anywhere is invalid.
    # (FSCK_MSG_NUL_IN_COMMIT).
    if "\0" in name:
        raise ValueError(f"NUL in name: {name!r}")
    if "\0" in mail:
        raise ValueError(f"NUL in mail: {mail!r}")

    # No name-email separators anywhere.
    # (FSCK_MSG_BAD_NAME)
    if "<" in name or ">" in name:
        raise ValueError(f"<> in name: {name!r}")
    # (FSCK_MSG_BAD_EMAIL)
    if "<" in mail or ">" in mail:
        raise ValueError(f"<> in mail: {mail!r}")

    # Git can't store fractional time; discard microseconds.
    if datetime_is_naive:
        moment = (time - EPOCH) // SECOND
        offset = '-0000'
    else:
        offmin = time.utcoffset() // MINUTE
        time_adj = time.replace(tzinfo=None) - MINUTE*offmin
        moment = (time_adj - EPOCH) // SECOND

        # Time is parsed a timestamp_t, which may be be large
        # but never negative (it's unsigned), or it'll most
        # certainly break Git.  (date_overflows in date.c)
        #
        # Actually, it doesn't even make it past fsck, since
        # "-" isn't a POSIX digit (FSCK_MSG_BAD_DATE).  Even
        # if it let it through, Git still wouldn't prepared
        # to handle negative timestamps.
        if moment < 0:
            raise ValueError(f"time precedes {EPOCH:%Y-%m-%d}: "
                             f"{time} (epoch {moment})")

        offset = rfc2822_formatzone(offmin)

    return f"{name} <{mail}> {moment} {offset}"


def rfc2822_timezone(off):
    """
    Format +{mmss} for Eastern regions with positive GMT offsets
    or -{mmss} for Western regions with negative GMT offsets.
    Regions with offset 0 is intentionally represented as +0000,
    as -0000 is reserved for UTC.
    """
    if off >= 0:
        ab_off = off
        prefix = '+'
    else:
        ab_off = -off
        prefix = '-'

    (mm, ss) = divmod(ab_off, 60)
    return f"{prefix}{mm:02}{ss:02}"


def commit(repo, tree, parents=None, author=None, committer=None, message=''):
    """
    Implements a subset of git-commit-tree(1).  Return a pygit2.Oid.
    To truly complete the commit cycle, a ref-update is necessary.

    Preferably pass all omittable arguments by name and not by position.
    """
    # Force EOL on every commit.
    #
    # I just can't stand commits without EOL... sorry lol. :P
    if message and message[-1] != "\n":
        message += "\n"
    text_payload = """\
tree {tree}
{parent}
author {author}
committer {committer}

{message}\
""".format(
        tree      = tree,
        parent    = "\n".join(f"parent {p}" for p in parents or ()),
        author    = author,
        committer = committer,
        message   = message,
    )
    payload = text_payload.encode('UTF-8')
    return repo.odb.write(pygit2.GIT_OBJECT_COMMIT, payload)
