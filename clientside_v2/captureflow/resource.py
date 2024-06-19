import platform

from opentelemetry.sdk.resources import Resource

from captureflow.config import CF_SERVICE_NAME


def get_resource():
    return Resource.create({"service.name": CF_SERVICE_NAME, "python_version": platform.python_version()})
