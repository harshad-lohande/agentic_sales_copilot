# app/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Loads and manages all configuration for the application.
    Reads from a .env file and environment variables.
    """
    # Configure Pydantic to load from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- API Keys & Secrets (from .env) ---
    OPENAI_API_KEY: str
    SENDGRID_API_KEY: str
    SLACK_BOT_TOKEN: str
    SLACK_CHANNEL_ID: str

    # --- Application Parameters ---
    SENDER_EMAIL: str = "user.name@example.com"
    REPLY_TO_EMAIL: str = "user.name@example.com"
    PROSPECTS_CSV_PATH: str = "prospects.csv"

    # --- Agent Model Names ---
    MANAGER_AGENT_MODEL: str = "gpt-4o"
    SDR_AGENT_MODEL: str = "gpt-4o"
    WRITER_AGENT_MODEL: str = "gpt-4o-mini"
    CAMAPIGN_SENDER_MODEL: str = "gpt-4o-mini"

# Create a single, importable instance of the settings
settings = Settings()
