"""Singleton secrets manager — loads credentials from environment."""

import os
import logging
from typing import Dict, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


class SecretsManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._openai_api_key = os.getenv("OPENAI_API_KEY")
        self._aws_region = os.getenv("AWS_REGION", "us-east-1")

        if not self._openai_api_key:
            logger.warning("OPENAI_API_KEY not set")

        self._initialized = True

    def get_openai_api_key(self) -> Optional[str]:
        return self._openai_api_key

    def get_aws_credentials(self) -> Dict[str, str]:
        return {"region": self._aws_region}


def get_secrets_manager() -> SecretsManager:
    return SecretsManager()
