import base64
import os

from dotenv import load_dotenv

load_dotenv(override=True)

GITHUB_APP_ID = os.getenv("GITHUB_APP_ID", "EMPTY_GITHUB_APP_ID")
GITHUB_APP_PRIVATE_KEY_BASE64 = os.getenv("GITHUB_APP_PRIVATE_KEY_BASE64", base64.b64encode(b"EMPTY_GITHUB_APP_PRIVATE_KEY_BASE64"))
OPENAI_KEY = os.getenv("OPENAI_KEY", "EMPTY_OPENAI_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
