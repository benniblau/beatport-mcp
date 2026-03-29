# beatport-mcp

MCP server wrapping the Beatport API v4 over HTTP Streamable transport.

## Quick reference

- **Entry point**: `server.py` — FastMCP server, tool definitions, lifespan setup
- **API client**: `beatport_client.py` — async HTTP client, OAuth auth, token refresh
- **Config**: all in `.env`, loaded via `python-dotenv`
- **Transport**: HTTP Streamable at `http://127.0.0.1:8000/mcp`
- **Python**: 3.10+, venv in `venv/`

## Running

```bash
source venv/bin/activate
python server.py
```

## Architecture

### Authentication (`beatport_client.py`)

Three-tier auth strategy in `ensure_authenticated()`:
1. Use current in-memory token if not expired
2. Refresh via `grant_type=refresh_token` if refresh_token available
3. Full OAuth `authorization_code` flow (login → authorize → token exchange)

The `client_id` is scraped from Beatport's docs page JS bundles at `https://api.beatport.com/static/btprt/*.js` — regex matches `API_CLIENT_ID: '...'`. Can be overridden via `BEATPORT_CLIENT_ID` env var.

### Tools (`server.py`)

Twelve tools registered via `@mcp.tool()`. Each takes a `ctx: Context` param (auto-excluded from MCP schema) to access the shared `BeatportClient` via `ctx.request_context.lifespan_context.client`.

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BEATPORT_USERNAME` | Yes | Beatport account username |
| `BEATPORT_PASSWORD` | Yes | Beatport account password |
| `BEATPORT_BASE_URL` | Yes | API base URL (`https://api.beatport.com/v4`) |
| `BEATPORT_ACCESS_TOKEN` | No | Pre-seeded access token |
| `BEATPORT_REFRESH_TOKEN` | No | Pre-seeded refresh token |
| `BEATPORT_TOKEN_EXPIRES_AT` | No | Token expiry as Unix timestamp |
| `BEATPORT_CLIENT_ID` | No | Override auto-scraped OAuth client_id |
| `MCP_HOST` | No | Server bind address (default: `127.0.0.1`) |
| `MCP_PORT` | No | Server port (default: `8000`) |
| `MCP_AUTH_TOKEN` | No | If set, all requests must include `Authorization: Bearer <token>` header |

## Dependencies

`mcp[cli]`, `httpx`, `python-dotenv` — see `requirements.txt`.

## API endpoints used

- `POST /auth/login/` — session login
- `GET /auth/o/authorize/` — OAuth authorize (returns code via 302)
- `POST /auth/o/token/` — token exchange and refresh
- `GET /my/account/` — current user
- `GET /my/beatport/labels/` — labels followed by current user
- `GET /my/beatport/artists/` — artists followed by current user
- `GET /catalog/search` — search tracks/releases
- `GET /catalog/tracks/{id}/` — track detail
- `GET /catalog/releases/` — release list (supports `label_id`, `artists_id`, `ordering` filters)
- `GET /catalog/releases/{id}/` — release detail
- `GET /catalog/releases/{id}/tracks/` — release tracklist
- `GET /catalog/artists/{id}/` — artist detail
- `GET /catalog/labels/{id}/` — label detail
