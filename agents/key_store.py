"""Persistent local key store for agent credentials.

Stores agent IDs and API keys in a JSON file so they survive across runs.
The key store supports register-or-recover: if an agent name already exists
in the store (and the server), it reuses the saved credentials instead of
failing with a 409 conflict.
"""

import json
import logging
import os
import stat
import tempfile
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
        """Atomically write the key store to prevent corruption on crash."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(self._data, indent=2, default=str)
        fd, tmp_path = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, str(self.path))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        try:
            self.path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
        except OSError:
            pass  # Windows ACLs don't support POSIX modes

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
