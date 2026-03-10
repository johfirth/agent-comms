import logging
import warnings

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_DEFAULT_ADMIN_KEY = "admin-dev-key-change-me"


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://agent_comms:agent_comms_dev@localhost:5432/agent_comms"
    admin_api_key: str = _DEFAULT_ADMIN_KEY

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

# --- Security: warn loudly if the default admin key is still in use ----------
# In production the ADMIN_API_KEY env-var (or .env) MUST override the default.
if settings.admin_api_key == _DEFAULT_ADMIN_KEY:
    _msg = (
        "SECURITY WARNING: Using the default admin API key. "
        "Set ADMIN_API_KEY in your environment or .env file before deploying."
    )
    logger.warning(_msg)
    warnings.warn(_msg, stacklevel=1)
