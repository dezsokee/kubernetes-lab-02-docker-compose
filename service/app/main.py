"""HTTP API for snipbox."""

import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app import __version__, db

_ID_BYTES = 6  # -> 8 characters of url-safe base64


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.connect()
    yield
    db.close()


app = FastAPI(
    title="snipbox",
    version=__version__,
    summary="Store short text snippets and read them back by id.",
    lifespan=lifespan,
)


class SnippetCreate(BaseModel):
    content: str = Field(min_length=1, max_length=64_000)
    title: str = Field(default="untitled", min_length=1, max_length=120)
    language: str = Field(default="text", min_length=1, max_length=32)


class Snippet(BaseModel):
    id: str
    title: str
    language: str
    content: str
    created_at: str


class SnippetList(BaseModel):
    total: int
    items: list[Snippet]


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"service": "snipbox", "version": __version__, "docs": "/docs"}


@app.get("/health", tags=["meta"])
def health() -> dict[str, object]:
    """Liveness probe: also proves the database is reachable."""
    return {"status": "ok", "snippets": db.count(), "db": db.database_target()}


@app.post("/snippets", status_code=201, tags=["snippets"])
def create_snippet(payload: SnippetCreate) -> Snippet:
    snippet_id = secrets.token_urlsafe(_ID_BYTES)
    row = db.insert(snippet_id, payload.title, payload.language, payload.content)
    return Snippet(**row)


@app.get("/snippets", tags=["snippets"])
def list_snippets(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> SnippetList:
    return SnippetList(
        total=db.count(),
        items=[Snippet(**row) for row in db.list_all(limit, offset)],
    )


@app.get("/snippets/{snippet_id}", tags=["snippets"])
def get_snippet(snippet_id: str) -> Snippet:
    row = db.get(snippet_id)
    if row is None:
        raise HTTPException(status_code=404, detail="snippet not found")
    return Snippet(**row)


@app.delete("/snippets/{snippet_id}", status_code=204, tags=["snippets"])
def delete_snippet(snippet_id: str) -> Response:
    if not db.delete(snippet_id):
        raise HTTPException(status_code=404, detail="snippet not found")
    return Response(status_code=204)
