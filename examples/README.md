This is an example app for testing CaptureFlow functionality.
It's copied from https://github.com/skatesham/fastapi-bigger-application


The idea is that after:
1. Instrumenting `fastapi-carshop` with captureflow-agent.
2. Adding minimal CaptureFlow-related configuration (`Dockerfile.cf` explaining how to run existing test suite)
3. Simulating some traffic data going through it.

CaptureFlow is going to be able to produce test suite characterizing existing endpoint behaviour.
