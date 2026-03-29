# beatport-mcp

An MCP (Model Context Protocol) server that exposes the [Beatport](https://beatport.com) API v4 as tools for LLMs. Uses the HTTP Streamable transport so any MCP client can connect over HTTP.

Authentication is based on the reverse-engineered OAuth flow from [beets-beatport4](https://github.com/Samik081/beets-beatport4).

## Prerequisites

- Python 3.10+
- A Beatport account (username & password)

## Setup

```bash
# Clone and enter the project
cd beatport-mcp

# Create a virtual environment and install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```env
# Required
BEATPORT_USERNAME=your_username
BEATPORT_PASSWORD=your_password
BEATPORT_BASE_URL=https://api.beatport.com/v4

# Optional — pre-seed tokens to skip login on first start.
# After first successful auth these are managed automatically in memory.
# If omitted, the server performs a full login on startup.
BEATPORT_ACCESS_TOKEN=
BEATPORT_REFRESH_TOKEN=
BEATPORT_TOKEN_EXPIRES_AT=
```

All configuration lives in `.env`. Nothing is hardcoded.

## Running the server

```bash
source venv/bin/activate
python server.py
```

The server starts on `http://127.0.0.1:8000/mcp`.

### Register with Claude Code

```bash
claude mcp add --transport http beatport-mcp http://127.0.0.1:8000/mcp
```

### Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

Then connect to `http://127.0.0.1:8000/mcp` in the inspector UI.

## Available tools

| Tool | Description | Inputs |
|------|-------------|--------|
| `search_tracks` | Search for tracks by query | `query` (str), `per_page` (int, default 10) |
| `search_releases` | Search for releases by query | `query` (str), `per_page` (int, default 10) |
| `get_track` | Get track details by ID | `track_id` (int) |
| `get_release` | Get release details by ID | `release_id` (int) |
| `get_release_tracks` | Get all tracks in a release | `release_id` (int), `per_page` (int, default 100) |
| `get_artist` | Get artist details by ID | `artist_id` (int) |
| `get_label` | Get label details by ID | `label_id` (int) |
| `get_my_account` | Get current user info | (none) |

All tools return JSON.

## Authentication

The server handles authentication automatically:

1. **On startup** — if `BEATPORT_ACCESS_TOKEN` and `BEATPORT_REFRESH_TOKEN` are set in `.env`, the server uses them directly without logging in.
2. **On token expiry** — the server automatically refreshes the token using the `refresh_token` grant. No manual intervention needed.
3. **On refresh failure** — falls back to a full OAuth login using your username and password.

The OAuth `client_id` is scraped automatically from Beatport's API docs page. You can optionally set `BEATPORT_CLIENT_ID` in `.env` to skip scraping.

## Project structure

```
beatport-mcp/
├── server.py              # MCP server — tool definitions and HTTP transport
├── beatport_client.py     # Async Beatport API v4 client with OAuth auth
├── requirements.txt       # Python dependencies
├── .env                   # Credentials and config (gitignored)
└── .gitignore
```

## Credits

Authentication flow adapted from [beets-beatport4](https://github.com/Samik081/beets-beatport4) by Samik081.
