"""Asynchronous Server Gateway Interface.

FastAPI is an ASGI app, so we simply create it
and return it.
"""

__all__ = ['Application', 'default']

import os
import datetime

import fastapi
import fastapi.responses
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import __version__
from . import can
from . import dbi
from . import git as gitmod


WIKI_REPO   = os.environ.get('WIKI_REPO',   '.')
WIKI_BRANCH = os.environ.get('WIKI_BRANCH', 'main')


def default():
    """Create default application."""
    return Application().to_asgi()


class _PageEdit(BaseModel):
    text: str


routes = fastapi.APIRouter()


@routes.get('/api/read')
def api_read(f: str):
    try:
        name = can.check_path(f)
    except ValueError as e:
        raise fastapi.HTTPException(400, str(e))
    if not can.can_read(name):
        raise fastapi.HTTPException(403, "read not allowed")
    try:
        repo = dbi.Repository(WIKI_REPO, WIKI_BRANCH)
    except Exception as e:
        raise fastapi.HTTPException(500, f"repo error: {e}")
    if repo.head is None:
        raise fastapi.HTTPException(404, "wiki is empty")
    try:
        wiki = repo.wiki()
        data = wiki.read(f"{name}.txt")
    except KeyError:
        raise fastapi.HTTPException(404, f"page not found: {name!r}")
    return fastapi.responses.Response(content=data, media_type='text/plain; charset=utf-8')


@routes.post('/api/post')
def api_post(f: str, body: _PageEdit, request: fastapi.Request):
    try:
        name = can.check_path(f)
    except ValueError as e:
        raise fastapi.HTTPException(400, str(e))
    if not can.can_write(name):
        raise fastapi.HTTPException(403, "write not allowed")
    data = body.text.encode('utf-8')
    try:
        repo = dbi.Repository(WIKI_REPO, WIKI_BRANCH)
        if repo.head is None:
            raise fastapi.HTTPException(503, "wiki not initialized")
        wiki = repo.wiki()
        wiki.write(f"{name}.txt", data)
        repo.join(wiki)
        host = (request.client.host if request.client else 'unknown')
        now  = datetime.datetime.utcnow()
        author = gitmod.mkgitid(host, 'www-data@wiki', now)
        repo.commit(author, f"Edit {name}")
    except fastapi.HTTPException:
        raise
    except ValueError as e:
        raise fastapi.HTTPException(409, str(e))
    except Exception as e:
        raise fastapi.HTTPException(500, f"commit error: {e}")
    return {'ok': True}


class Application:
    title = "DK-Wiki backend"
    description = "Default implementation"
    version = __version__

    def __init__(self):
        pass

    def to_asgi(self):
        app = fastapi.FastAPI(
            title       = self.title,
            description = self.description,
            version     = self.version,
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=['*'],
            allow_methods=['GET', 'POST'],
            allow_headers=['Content-Type'],
        )
        app.include_router(routes)
        return app
