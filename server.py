"""Beatport MCP Server - HTTP Streamable MCP server for the Beatport API v4."""

import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP

from beatport_client import BeatportClient

load_dotenv()


@dataclass
class AppContext:
    client: BeatportClient


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    expires_at = os.environ.get("BEATPORT_TOKEN_EXPIRES_AT")
    client = BeatportClient(
        username=os.environ["BEATPORT_USERNAME"],
        password=os.environ["BEATPORT_PASSWORD"],
        base_url=os.environ["BEATPORT_BASE_URL"],
        access_token=os.environ.get("BEATPORT_ACCESS_TOKEN"),
        refresh_token=os.environ.get("BEATPORT_REFRESH_TOKEN"),
        token_expires_at=float(expires_at) if expires_at else None,
    )
    try:
        yield AppContext(client=client)
    finally:
        await client.close()


mcp = FastMCP(
    "beatport-mcp",
    lifespan=app_lifespan,
)


def _get_client(ctx) -> BeatportClient:
    return ctx.request_context.lifespan_context.client


@mcp.tool()
async def search_tracks(query: str, ctx: Context, per_page: int = 10) -> str:
    """Search for tracks on Beatport by query string.

    Returns tracks with id, name, artists, bpm, key, genre, mix_name, and release info.
    """
    client = _get_client(ctx)
    results = await client.search_tracks(query, per_page=per_page)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def search_releases(query: str, ctx: Context, per_page: int = 10) -> str:
    """Search for releases (albums, EPs, singles) on Beatport by query string.

    Returns releases with id, name, artists, label, catalog_number, and publish_date.
    """
    client = _get_client(ctx)
    results = await client.search_releases(query, per_page=per_page)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_track(track_id: int, ctx: Context) -> str:
    """Get detailed information about a specific Beatport track by its ID.

    Returns id, name, artists, length_ms, bpm, key, genre, sub_genre, mix_name, release, and remixers.
    """
    client = _get_client(ctx)
    result = await client.get_track(track_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def get_release(release_id: int, ctx: Context) -> str:
    """Get detailed information about a specific Beatport release by its ID.

    Returns id, name, artists, type, label, catalog_number, url, and publish_date.
    """
    client = _get_client(ctx)
    result = await client.get_release(release_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def get_release_tracks(release_id: int, ctx: Context, per_page: int = 100) -> str:
    """Get all tracks in a specific Beatport release.

    Returns a list of track objects with full metadata.
    """
    client = _get_client(ctx)
    results = await client.get_release_tracks(release_id, per_page=per_page)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_artist(artist_id: int, ctx: Context) -> str:
    """Get details about a Beatport artist by their ID.

    Returns artist information including name and associated releases.
    """
    client = _get_client(ctx)
    result = await client.get_artist(artist_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def get_label(label_id: int, ctx: Context) -> str:
    """Get details about a Beatport record label by its ID.

    Returns label information including name and catalog details.
    """
    client = _get_client(ctx)
    result = await client.get_label(label_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def get_my_account(ctx: Context) -> str:
    """Get the current authenticated Beatport user's account information.

    Returns id, email, and username.
    """
    client = _get_client(ctx)
    result = await client.get_my_account()
    return json.dumps(result, indent=2, default=str)


def main():
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
