# CaptureFlow Tracer

## Overview

The CaptureFlow Tracer is a Python package crafted for in-depth tracing of function calls within Python applications. Its primary function is to capture and relay execution data to the CaptureFlow server-side system for decision making.

## Performance Considerations

The current implementation of the Tracer module utilizes the `sys.settrace` module ([Python Doc](https://docs.python.org/3/library/sys.html#sys.settrace)), leading to two outcomes:

- **Detailed Logging**: Captures verbose logs with debugger-level insight into method calls, variable states, and more.
- **Performance Impact**: The logging method significantly affects application performance.

## Building and Testing Locally

To begin, ensure you have Python 3.8+, `venv`, and the `requirements-dev.txt` installed.

Explore the `clientside/examples` directory for sample applications suitable for testing. For local package building with source code, each folder contains an `./install_package.sh` script. After building, run a local server and cURL some endpoints to simulate a real-life workflow.

If the environment variable `CAPTUREFLOW_DEV_SERVER` is set to `"true"`, trace JSON objects will be dumped locally for further inspection. Additionally, running the `serverside` Docker container allows you to observe trace data ingestion in real-time.

For an **example of the data structure** captured by the tracer, you can check [sample_trace_with_exception.json](https://github.com/CaptureFlow/captureflow-py/blob/main/serverside/tests/assets/sample_trace_with_exception.json).

## Roadmap for Optimization

We need to balancing trace detail with performance, planning enhancements for the Tracer's efficiency:

#### Short-Term Objectives

- **Selective Tracing**: Implement a "verbosity" parameter for targeted tracing, focusing on relevant trace events. For example, we need to "sample" a representative subset of requests instead of capturing all of them.
- **Framework Integration and Middleware Enhancements**:
  - Research if it's feasible to develop middleware/patching for popular frameworks to ship data of similar detalization.
  - Explore integration with tracing standards like OpenTelemetry for better application monitoring.

#### Long-Term Objectives

- **Performance vs. Data Utility for CodeGen**: Focus on collecting essential data for high-quality server-side improvements. We're pinpointing the specific data subset required to minimize performance disruption while maximizing optimization quality.