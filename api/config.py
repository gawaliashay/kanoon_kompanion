import os
import json
from typing import Dict, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application settings
    project_name: str = os.getenv("PROJECT_NAME", "document_portal_pro")
    environment: str = os.getenv("ENV", "production")
    container_port: int = int(os.getenv("CONTAINER_PORT", "8080"))
    
    # AWS Settings
    aws_region: str = os.getenv("AWS_REGION", "ap-south-1")
    # Require CloudFormation/ECS to provide this
    s3_bucket: str = os.environ["S3_BUCKET"]

    # Secrets Manager (injected into env var API_KEYS by ECS)
    _raw_api_keys: Optional[str] = os.getenv("API_KEYS")

    @property
    def api_keys(self) -> Dict[str, str]:
        """
        Returns API keys as a dictionary.
        - If the secret is plain text → returns {"default": "<value>"}.
        - If the secret is JSON → parses and returns the dict.
        """
        if not self._raw_api_keys:
            return {}

        try:
            return json.loads(self._raw_api_keys)
        except json.JSONDecodeError:
            return {"default": self._raw_api_keys}

    class Config:
        env_file = ".env"


settings = Settings()
