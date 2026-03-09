"""HTTP client wrapper for the Agent Communication Server."""

import os
import httpx


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

    def _headers(self, admin: bool = False) -> dict[str, str]:
        key = self.admin_api_key if admin else self.api_key
        return {"X-API-Key": key, "Content-Type": "application/json"}

    async def get(self, path: str, params: dict | None = None, admin: bool = False) -> dict | list:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as c:
            resp = await c.get(path, headers=self._headers(admin), params=params)
            resp.raise_for_status()
            return resp.json()

    async def post(self, path: str, json: dict | None = None, admin: bool = False) -> dict:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as c:
            resp = await c.post(path, headers=self._headers(admin), json=json)
            resp.raise_for_status()
            return resp.json()

    async def patch(self, path: str, json: dict | None = None, admin: bool = False) -> dict:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as c:
            resp = await c.patch(path, headers=self._headers(admin), json=json)
            resp.raise_for_status()
            return resp.json()

    async def put(self, path: str, json: dict | None = None, admin: bool = False) -> dict:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as c:
            resp = await c.put(path, headers=self._headers(admin), json=json)
            resp.raise_for_status()
            return resp.json()
