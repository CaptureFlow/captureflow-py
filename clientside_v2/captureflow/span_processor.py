import inspect
from logging import getLogger
from pathlib import Path
from types import CodeType, FrameType

import opentelemetry
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor

import captureflow

logger = getLogger(__name__)

# Set up constants for determining user code
CWD = Path(".").resolve()
PREFIXES = (
    str(Path(opentelemetry.sdk.trace.__file__).parent.parent.parent.parent),
    str(Path(inspect.__file__).parent),
    str(Path(captureflow.__file__).parent),
)


def get_stack_info_from_frame(frame: FrameType):
    """
    Extract file path, function name, and line number from a frame.
    """
    code = frame.f_code
    info = {"code.filepath": get_relative_filepath(code.co_filename)}
    if code.co_name != "<module>":
        info["code.function"] = code.co_name
    info["code.lineno"] = frame.f_lineno
    return info


def get_relative_filepath(file: str) -> str:
    """
    Convert absolute file path to relative path from CWD if possible.
    """
    path = Path(file)
    try:
        return str(path.relative_to(CWD))
    except ValueError:
        return str(path)


def is_user_code(code: CodeType) -> bool:
    """
    Determine if a code object is from user code.
    """
    return not any(str(Path(code.co_filename).absolute()).startswith(prefix) for prefix in PREFIXES)


def get_user_stack_info():
    """
    Get the stack info for the first calling frame in user code.
    """
    frame = inspect.currentframe()
    while frame:
        if is_user_code(frame.f_code):
            return get_stack_info_from_frame(frame)
        frame = frame.f_back
    return {}


class FrameInfoSpanProcessor(SpanProcessor):
    def on_start(self, span: Span, parent_context):
        """
        Add user stack info attributes to the span when it starts.
        """
        stack_info = get_user_stack_info()
        for key, value in stack_info.items():
            span.set_attribute(key, value)

    def on_end(self, span: ReadableSpan):
        pass

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis: int = 30000):
        pass
