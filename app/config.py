from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://agent_comms:agent_comms_dev@localhost:5432/agent_comms"
    admin_api_key: str = "admin-dev-key-change-me"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
