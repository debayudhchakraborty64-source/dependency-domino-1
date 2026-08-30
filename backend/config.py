"""
Dependency Domino - FastAPI Backend
Configuration and settings management
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # watsonx.ai – primary env var names per specification
    watsonx_apikey: str = ""           # WATSONX_APIKEY
    watsonx_project_id: str = ""       # WATSONX_PROJECT_ID
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"  # WATSONX_URL
    watsonx_model_id: str = ""         # WATSONX_MODEL_ID

    # Legacy alias – accept WATSONX_API_KEY as fallback (older .env files)
    watsonx_api_key: str = ""

    # App
    app_env: str = "development"
    max_upload_size_mb: int = 50
    upload_dir: str = "./uploads"
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:3001"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def effective_api_key(self) -> str:
        """Return the API key, preferring WATSONX_APIKEY over legacy WATSONX_API_KEY."""
        return self.watsonx_apikey or self.watsonx_api_key

    @property
    def watsonx_configured(self) -> bool:
        """True only when credentials AND project ID are present."""
        return bool(self.effective_api_key and self.watsonx_project_id)

    @property
    def watsonx_model_configured(self) -> bool:
        """True when a model ID has been provided."""
        return bool(self.watsonx_model_id)

    @property
    def watsonx_status(self) -> str:
        """Safe status string – never exposes credentials."""
        if not self.watsonx_configured:
            return "NOT_CONFIGURED"
        if not self.watsonx_model_configured:
            return "NO_MODEL"
        return "CONFIGURED"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
