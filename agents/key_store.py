"""Persistent local key store for agent credentials.

Stores agent IDs and API keys in a JSON file so they survive across runs.
The key store supports register-or-recover: if an agent name already exists
in the store (and the server), it reuses the saved credentials instead of
failing with a 409 conflict.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_STORE_PATH = Path(__file__).parent / "keys.json"


class KeyStore:
    """Read/write agent credentials to a local JSON file."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else DEFAULT_STORE_PATH
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
                logger.info("Loaded %d agent(s) from %s", len(self._data), self.path)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load key store: %s", exc)
                self._data = {}
        else:
            self._data = {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, indent=2, default=str),
            encoding="utf-8",
        )

    def get(self, agent_name: str) -> dict | None:
        """Return stored credentials for an agent, or None if not found."""
        return self._data.get(agent_name)

    def save_agent(self, agent_name: str, agent_id: str, api_key: str, display_name: str = ""):
        """Persist an agent's credentials."""
        self._data[agent_name] = {
            "id": agent_id,
            "api_key": api_key,
            "display_name": display_name,
        }
        self._save()
        logger.info("Saved credentials for '%s' to key store", agent_name)

    def update_key(self, agent_name: str, new_api_key: str):
        """Update the API key for an existing agent."""
        if agent_name in self._data:
            self._data[agent_name]["api_key"] = new_api_key
            self._save()

    def list_agents(self) -> dict[str, dict]:
        """Return all stored agents."""
        return dict(self._data)

    def remove(self, agent_name: str):
        """Remove an agent from the store."""
        self._data.pop(agent_name, None)
        self._save()
