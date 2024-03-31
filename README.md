# captureflow-py

Leverage the deep context embedded in your deployed app to fuel LLMs, turning boring maintenance tasks into an AI-enhanced evolution:

- **Context-Driven Code Enhancement**: Improve your code quality by leveraging the deep contextual insights provided by LLM agents observing traces from production.
- **Trace-Based Auto-Debugging & Test Creation:** Transform traces into a foundation for generating tests and automating bug fix implementation.
- **Execution Graph "Replays" as new way of validating suggestions:** Use traces to simulate specific parts of the execution graph, ensuring the validity of suggestions and mitigating the risk of hallucinations.

## Project timeline

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

#### Serverside

You will need to deploy `fastapi` app together with `redis` instance.

```sh
docker compose up --build
```
