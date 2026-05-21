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
from . import git
from . import push
from . import rpxy


WIKI_REPO   = os.environ.get('WIKI_REPO',   '.')
WIKI_BRANCH = os.environ.get('WIKI_BRANCH', 'main')


def default():
    """Create default application."""
    return Application().to_asgi()


class PageEdit(BaseModel):
    text: str


class Application:
    title = "DK-Wiki backend"
    description = "Default implementation"
    version = __version__

    def __init__(self):
        self.routes = fastapi.APIRouter()
        self.routes.add_api_route(
            "/api/ping",
            self.api_ping,
            methods=["GET"],
        )
        self.routes.add_api_route(
            "/api/read",
            self.api_read,
            methods=["GET"],
        )
        self.routes.add_api_route(
            "/api/post",
            self.api_post,
            methods=["POST"],
        )

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
        app.include_router(self.routes)
        return app

    def api_ping(self):
        """
        GET /api/ping HTTP/1.1
        """
        return {"ok": True}

    def api_read(self, f: str):
        """
        GET /api/read?f=PATH HTTP/1.1
        """
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
        # TODO: Use REST; I don't want to deal with charset ever
        return fastapi.responses.Response(content=data, media_type='text/plain; charset=utf-8')

    def api_post(self, f: str, body: PageEdit, request: fastapi.Request,
                 background_tasks: fastapi.BackgroundTasks):
        """
        GET /api/post?f=PATH HTTP/1.1
        Content-Type: application/json

        {"text": ...}
        """
        try:
            name = can.check_path(f)
        except ValueError as e:
            raise fastapi.HTTPException(400, str(e))
        if not can.can_write(name):
            raise fastapi.HTTPException(403, "write not allowed")
        try:
            data = body.text.encode('utf-8')
        except UnicodeEncodeError as e:
            raise fastapi.HTTPException(400, f"invalid UTF-8: {e}")
        if len(data) > 64 * 1024:
            raise fastapi.HTTPException(413, "page too large: limit is 64 KiB")
        try:
            repo = dbi.Repository(WIKI_REPO, WIKI_BRANCH)
            if repo.head is None:
                raise fastapi.HTTPException(503, "wiki not initialized")
            wiki = repo.wiki()
            wiki.write(f"{name}.txt", data)
            repo.join(wiki)
            try:
                host = rpxy.peer_address(request)
            except ValueError:
                raise fastapi.HTTPException(500, "server misconfigured: cannot determine client address")
            now  = datetime.datetime.utcnow()
            try:
                ident = repo.identity()
                my_name = ident.name
                my_mail = ident.email
            except LookupError:
                # KeyError: "config value 'user.name' was not found"
                my_name = 'www'
                my_mail = 'www@engine.cs472.endfind.me'
            author = git.mkgitid(host, my_mail, now)
            committer = git.mkgitid(my_name, my_mail, now)
            repo.commit(author, f"Edit {name}", committer)
            background_tasks.add_task(push.push, WIKI_REPO, WIKI_BRANCH)
        except fastapi.HTTPException:
            raise
        except ValueError as e:
            raise fastapi.HTTPException(409, str(e))
        except Exception as e:
            raise fastapi.HTTPException(500, f"commit error: {e}")
        return {'ok': True}
