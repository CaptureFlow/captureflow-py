from logging import getLogger

from opentelemetry.instrumentation.distro import BaseDistro
from opentelemetry.trace import set_tracer_provider

from captureflow.instrumentation import apply_instrumentation
from captureflow.resource import get_resource
from captureflow.tracer_provider import get_tracer_provider

logger = getLogger(__name__)

class CaptureFlowDistro(BaseDistro):
    def _configure(self, **kwargs):
        logger.error("CaptureFlow instumentation initialized")

        # Setup basic tracer
        resource = get_resource()
        tracer_provider = get_tracer_provider(resource)
        set_tracer_provider(tracer_provider)

        # Make sure libraries of interest are instrumented
        apply_instrumentation(tracer_provider)
