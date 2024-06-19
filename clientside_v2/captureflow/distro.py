from logging import getLogger

from opentelemetry.instrumentation.distro import BaseDistro
from opentelemetry.trace import set_tracer_provider

from captureflow.instrumentation import apply_instrumentation
from captureflow.resource import get_resource
from captureflow.span_processor import FrameInfoSpanProcessor
from captureflow.tracer_provider import get_tracer_provider

logger = getLogger(__name__)


class CaptureFlowDistro(BaseDistro):
    def _configure(self, **kwargs):
        logger.error("CaptureFlow instrumentation initialized")

        # Setup basic tracer
        resource = get_resource()
        tracer_provider = get_tracer_provider(resource)

        # Add custom span processor to include frame information
        frame_info_span_processor = FrameInfoSpanProcessor()
        tracer_provider.add_span_processor(frame_info_span_processor)

        set_tracer_provider(tracer_provider)

        # Make sure libraries of interest are instrumented
        apply_instrumentation(tracer_provider)
