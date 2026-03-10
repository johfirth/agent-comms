"""HTTP client wrapper for the Agent Communication Server."""

import os

import httpx


class AgentCommsError(Exception):
    """Clean error raised when the agent-comms API returns an error.

    Contains a sanitised message safe to surface to LLMs — no URLs,
    headers, or API keys are included.
    """

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class AgentCommsClient:
    """Thin async httpx wrapper that holds base_url and auth headers."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        admin_api_key: str | None = None,
    ):
        self.base_url = (base_url or os.environ.get("AGENT_COMMS_URL", "http://localhost:8000")).rstrip("/")
        self.api_key = api_key or os.environ.get("AGENT_COMMS_API_KEY", "")
        self.admin_api_key = admin_api_key or os.environ.get("AGENT_COMMS_ADMIN_KEY", "")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a persistent httpx client, creating one if needed."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self._client

    async def close(self):
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.close()
            self._client = None

    def _headers(self, admin: bool = False) -> dict[str, str]:
        key = self.admin_api_key if admin else self.api_key
        return {"X-API-Key": key, "Content-Type": "application/json"}

    @staticmethod
    def _handle_http_error(exc: httpx.HTTPStatusError) -> None:
        """Translate an httpx HTTP error into a clean AgentCommsError."""
        status = exc.response.status_code
        try:
            body = exc.response.json()
            detail = body.get("detail", str(body))
        except Exception:
            detail = exc.response.text or "Unknown error"
        raise AgentCommsError(status, f"API error ({status}): {detail}") from None

    @staticmethod
    def _handle_connect_error() -> None:
        raise AgentCommsError(
            0, "Cannot connect to agent-comms server. Is it running?"
        ) from None

    @staticmethod
    def _handle_timeout() -> None:
        raise AgentCommsError(0, "Request to agent-comms server timed out.") from None

    async def get(self, path: str, params: dict | None = None, admin: bool = False) -> dict | list:
        c = await self._get_client()
        try:
            resp = await c.get(path, headers=self._headers(admin), params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc)
            raise  # unreachable — _handle_http_error always raises
        except httpx.ConnectError:
            self._handle_connect_error()
            raise
        except httpx.TimeoutException:
            self._handle_timeout()
            raise

    async def post(self, path: str, json: dict | None = None, admin: bool = False) -> dict:
        c = await self._get_client()
        try:
            resp = await c.post(path, headers=self._headers(admin), json=json)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc)
            raise
        except httpx.ConnectError:
            self._handle_connect_error()
            raise
        except httpx.TimeoutException:
            self._handle_timeout()
            raise

    async def patch(self, path: str, json: dict | None = None, admin: bool = False) -> dict:
        c = await self._get_client()
        try:
            resp = await c.patch(path, headers=self._headers(admin), json=json)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc)
            raise
        except httpx.ConnectError:
            self._handle_connect_error()
            raise
        except httpx.TimeoutException:
            self._handle_timeout()
            raise

    async def put(self, path: str, json: dict | None = None, admin: bool = False) -> dict:
        c = await self._get_client()
        try:
            resp = await c.put(path, headers=self._headers(admin), json=json)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc)
            raise
        except httpx.ConnectError:
            self._handle_connect_error()
            raise
        except httpx.TimeoutException:
            self._handle_timeout()
            raise
