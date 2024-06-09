import os

from dotenv import load_dotenv

load_dotenv(override=True)

CF_SERVICE_NAME = os.getenv("CF_SERVICE_NAME", "default_service_name")
CF_DEBUG = os.getenv("CF_DEBUG", False)
