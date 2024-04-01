# captureflow-py

Leverage LLMs not only to craft new software components but also to maintain and improve your existing repos. Software maintenance consumes a significant portion of dev time, yet **deployed applications are already rich with embedded context**.

By gathering and tracing data from production applications, we can unlock new approaches to automatic bug fixing and test generation. Real-time processing isn't our main concern; what we prioritize are reliable and meaningful improvements. 


## Main components

![Alt text](./assets/main-chart.svg)

1. Backend HTTP server, enhanced with the captureflow-clientside library.
2. The captureflow-backend system for trace storage and orchestration.
3. AI connector.
4. Version control connector.

**Support is currently limited to Python, OpenAI, and GitHub.**

## Roadmap / Where are we

| No. | Task                                                                                                      | State       |
|-----|-----------------------------------------------------------------------------------------------------------|-------------|
| 1   | Implement end-to-end pipeline: tracer and server.                                                         |    ✅     |
| 1.1 | Tracer outputs JSONs that represent Python execution frames.                                              | ✅        |
| 1.2 | Server stores incoming traces and able to enrich execution graph with GitHub metadata, such as function implementation. | ✅        |
| 2   | First heuristic method for MR generation. Only focus on method as optimization unit.                      | ✅ |
| 3   | Automated code fixes on exception: Utilize exception traces and execution context to propose targeted fixes for identified bugs.  | ✅ |
| 3.1 | **More benchmarking for sophisticated scenarios**                                                                                       | 🔨   |
| 4 | Utilize trace data to introduce a **new testing phase** for system code **mutations**, focusing on HTTP servers. Explore sandbox environments and **traffic replay** while simulating state changes by mocking relevant modules. | 🔨        |
| 5   | Extend existing test cases using accumulated traces data (more realistic mock data, new scenarios)                                                                 |       📝     |
| 6 | Improve RAG pipeline: fetch similar modules from code embeddings for reference; Implement ctags and more standardized methods of code parsing. | 📝        |


## Setup

#### Clientside

```sh
pip install captureflow-agent
```

```python
from captureflow.tracer import Tracer
tracer = Tracer(
    repo_url="https://github.com/CaptureFlow/captureflow-py",
    server_base_url="http://127.0.0.1:8000",
)

@app.get("/")
@tracer.trace_endpoint
def process_data(request):
    response = do_stuff(request)
    ...
```

Please check [clientside/README](https://github.com/CaptureFlow/captureflow-py/blob/main/clientside/README.md). 

#### Serverside

You will need to deploy `fastapi` app together with `redis` instance.

```sh
docker compose up --build
```

Please check [serverside/README](https://github.com/CaptureFlow/captureflow-py/blob/main/serverside/README.md).
