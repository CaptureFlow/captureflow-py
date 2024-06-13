import captureflow
import inspect
import opentelemetry

from logging import getLogger
from functools import lru_cache
from pathlib import Path
from types import CodeType, FrameType
from typing import TypedDict
from opentelemetry.sdk.trace import Span, ReadableSpan, SpanProcessor

logger = getLogger(__name__)

StackInfo = TypedDict('StackInfo', {'code.filepath': str, 'code.lineno': int, 'code.function': str}, total=False)

_CWD = Path('.').resolve()
SITE_PACKAGES_DIR = str(Path(opentelemetry.sdk.trace.__file__).parent.parent.parent.parent.absolute())
PYTHON_LIB_DIR = str(Path(inspect.__file__).parent.absolute())
CAPTUREFLOW_DIR = str(Path(captureflow.__file__).parent.absolute())
PREFIXES = (SITE_PACKAGES_DIR, PYTHON_LIB_DIR, CAPTUREFLOW_DIR)

def get_relative_filepath(file: str) -> str:
    """
    Convert absolute file path to relative path from CWD if possible.
    """
    path = Path(file)
    try:
        return str(path.relative_to(_CWD))
    except ValueError:
        return str(path)

@lru_cache(maxsize=2048)
def get_code_object_info(code: CodeType) -> StackInfo:
    """
    Extract file path, function name, and line number from code object.
    """
    info = {'code.filepath': get_relative_filepath(code.co_filename)}
    if code.co_name != '<module>':
        info['code.function'] = code.co_name
    info['code.lineno'] = code.co_firstlineno
    return info

def get_stack_info_from_frame(frame: FrameType) -> StackInfo:
    """
    Get stack info from a given frame.
    """
    return {
        **get_code_object_info(frame.f_code),
        'code.lineno': frame.f_lineno,
    }

@lru_cache(maxsize=8192)
def is_user_code(code: CodeType) -> bool:
    """
    Determine if a code object is from user code.
    """
    return not any(str(Path(code.co_filename).absolute()).startswith(prefix) for prefix in PREFIXES)

def get_user_stack_info() -> StackInfo:
    """
    From instrumented/traced methods, find first piece of user code
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