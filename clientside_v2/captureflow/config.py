# captureflow/config.py
import os

from dotenv import load_dotenv

load_dotenv(override=True)

CF_SERVICE_NAME = os.getenv("CF_SERVICE_NAME", "default_service_name")
CF_DEBUG = os.getenv("CF_DEBUG", False)
CF_OTLP_ENDPOINT = os.getenv("CF_OTLP_ENDPOINT", "http://localhost:4317")  # gRPC OTLP by default
