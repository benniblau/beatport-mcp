"""Async client for the Beatport API v4 with OAuth authentication."""

import os
import re
import time
from urllib.parse import parse_qs, urlparse

import httpx

TOKEN_EXPIRY_BUFFER = 30
USER_AGENT = "beatport-mcp/0.1.0"

SCRIPT_SRC_PATTERN = re.compile(r'src=.(.*?\.js)')
CLIENT_ID_PATTERN = re.compile(r"API_CLIENT_ID:\s*['\"]([^'\"]+)['\"]")


class BeatportAuthError(Exception):
    pass


class BeatportClient:
    def __init__(
        self,
        username: str,
        password: str,
        base_url: str,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expires_at: float | None = None,
    ):
        self.username = username
        self.password = password
        self.base_url = base_url.rstrip("/")
        self.redirect_uri = f"{self.base_url}/auth/o/post-message/"
        self.client_id: str | None = os.environ.get("BEATPORT_CLIENT_ID")
        self.token: dict | None = None
        if access_token:
            self.token = {
                "access_token": access_token,
                "refresh_token": refresh_token or "",
                "expires_at": token_expires_at or 0,
            }
        self._http = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=30.0,
            follow_redirects=True,
        )

    async def close(self):
        await self._http.aclose()

    # ── Authentication ──────────────────────────────────────────────

    async def ensure_authenticated(self):
        """Ensure we have a valid access token, refreshing or re-authenticating if needed."""
        # Token exists and not expired
        if self.token and time.time() + TOKEN_EXPIRY_BUFFER < self.token.get("expires_at", 0):
            return

        # Token expired but we have a refresh_token — try refreshing
        if self.token and self.token.get("refresh_token"):
            try:
                await self._refresh_token()
                return
            except Exception:
                pass

        # No token at all, or refresh failed — full login flow
        await self._full_auth_flow()

    async def _refresh_token(self):
        """Use the refresh_token to obtain a new access_token."""
        if not self.client_id:
            self.client_id = await self._fetch_client_id()

        resp = await self._http.post(
            f"{self.base_url}/auth/o/token/",
            params={
                "grant_type": "refresh_token",
                "refresh_token": self.token["refresh_token"],
                "client_id": self.client_id,
            },
        )
        if resp.status_code != 200:
            raise BeatportAuthError(
                f"Token refresh failed with status {resp.status_code}: {resp.text}"
            )

        token_data = resp.json()
        self.token = {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", self.token.get("refresh_token", "")),
            "expires_at": time.time() + token_data.get("expires_in", 3600),
        }

    async def _full_auth_flow(self):
        """Run the complete OAuth authorization_code flow."""
        if not self.client_id:
            self.client_id = await self._fetch_client_id()

        # Use a separate client with cookies for the auth flow
        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=30.0,
        ) as auth_client:
            # Step 1: Login to get session cookies
            login_resp = await auth_client.post(
                f"{self.base_url}/auth/login/",
                json={"username": self.username, "password": self.password},
            )
            if login_resp.status_code not in (200, 201, 204):
                raise BeatportAuthError(
                    f"Login failed with status {login_resp.status_code}: {login_resp.text}"
                )

            # Step 2: Get authorization code
            authorize_resp = await auth_client.get(
                f"{self.base_url}/auth/o/authorize/",
                params={
                    "response_type": "code",
                    "client_id": self.client_id,
                    "redirect_uri": self.redirect_uri,
                },
                follow_redirects=False,
            )
            if authorize_resp.status_code not in (301, 302, 303, 307, 308):
                raise BeatportAuthError(
                    f"Authorization failed with status {authorize_resp.status_code}: {authorize_resp.text}"
                )

            location = authorize_resp.headers.get("location", "")
            parsed = urlparse(location)
            code_values = parse_qs(parsed.query).get("code") or parse_qs(parsed.fragment).get("code")
            if not code_values:
                raise BeatportAuthError(f"No auth code in redirect: {location}")
            auth_code = code_values[0]

            # Step 3: Exchange code for token
            token_resp = await auth_client.post(
                f"{self.base_url}/auth/o/token/",
                params={
                    "code": auth_code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                    "client_id": self.client_id,
                },
            )
            if token_resp.status_code != 200:
                raise BeatportAuthError(
                    f"Token exchange failed with status {token_resp.status_code}: {token_resp.text}"
                )

            token_data = token_resp.json()
            self.token = {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token", ""),
                "expires_at": time.time() + token_data.get("expires_in", 3600),
            }

    async def _fetch_client_id(self) -> str:
        """Scrape the client_id from Beatport's API docs page."""
        docs_resp = await self._http.get(f"{self.base_url}/docs/")
        docs_resp.raise_for_status()

        script_urls = SCRIPT_SRC_PATTERN.findall(docs_resp.text)
        for script_url in script_urls:
            if not script_url.startswith("http"):
                parsed_base = urlparse(self.base_url)
                script_url = f"{parsed_base.scheme}://{parsed_base.netloc}{script_url}"
            try:
                js_resp = await self._http.get(script_url)
                js_resp.raise_for_status()
                match = CLIENT_ID_PATTERN.search(js_resp.text)
                if match:
                    return match.group(1)
            except Exception:
                continue

        raise BeatportAuthError("Could not scrape client_id from Beatport docs")

    # ── API Methods ─────────────────────────────────────────────────

    async def _api_get(self, endpoint: str, **params) -> dict | list:
        """Make an authenticated GET request to the Beatport API."""
        await self.ensure_authenticated()
        resp = await self._http.get(
            f"{self.base_url}{endpoint}",
            params=params if params else None,
            headers={"Authorization": f"Bearer {self.token['access_token']}"},
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return data

    async def get_my_account(self) -> dict:
        return await self._api_get("/my/account/")

    async def search_tracks(self, query: str, per_page: int = 10) -> list:
        return await self._api_get("/catalog/search", q=query, type="tracks", per_page=per_page)

    async def search_releases(self, query: str, per_page: int = 10) -> list:
        return await self._api_get("/catalog/search", q=query, type="releases", per_page=per_page)

    async def get_track(self, track_id: int) -> dict:
        return await self._api_get(f"/catalog/tracks/{track_id}/")

    async def get_release(self, release_id: int) -> dict:
        return await self._api_get(f"/catalog/releases/{release_id}/")

    async def get_release_tracks(self, release_id: int, per_page: int = 100) -> list:
        return await self._api_get(f"/catalog/releases/{release_id}/tracks/", per_page=per_page)

    async def get_artist(self, artist_id: int) -> dict:
        return await self._api_get(f"/catalog/artists/{artist_id}/")

    async def get_label(self, label_id: int) -> dict:
        return await self._api_get(f"/catalog/labels/{label_id}/")
