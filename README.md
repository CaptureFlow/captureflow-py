# captureflow-py

Leverage the deep context embedded in your deployed app to fuel LLMs, turning boring maintenance tasks into an AI-enhanced evolution, all while keeping a human in the loop.

- **Context-Driven Code Enhancement**: Improve your code quality by leveraging the deep contextual insights provided by LLM agents observing traces from production.
- **Trace-Based Test Creation & Auto-Debugging:** Transform traces into a robust foundation for generating tests and automating bug fix implementation.
- **Execution Graph "Replays" as new way of validating suggestions:** Use traces to simulate specific parts of the execution graph, ensuring the validity of suggestions and mitigating the risk of hallucinations.

## Project timeline

| No. | Task                                                                                                      | State       |
|-----|-----------------------------------------------------------------------------------------------------------|-------------|
| 1   | Implement end-to-end pipeline: tracer and server.                                                         |    ✅     |
| 1.1 | Tracer outputs JSONs that represent Python execution frames.                                              | ✅        |
| 1.2 | Server stores incoming traces and able to enrich execution graph with GitHub metadata, such as function implementation. | ✅        |
| 2   | First heuristic method for MR generation. Only focus on method as optimization unit.                      | ✅ |
| 3   | First heuristic method for LLM-based MR validation.                                                       | ✅ |
| 4   | Improve RAG pipeline for code-generation.                                                                 |       🔨     |
| 4.1 | Send more relevant modules than just parent_function and child_functions; Implement ctags and more standardized methods of code parsing. | 🔨        |
| 5   | Procedural / sandbox based AI-suggestion validation.                                                      | 📝   |
| 6   | Attempt to fetch relevant tests.                                                                          |             |
| 6.1 | Must be do-able to join execution graph during test execution with acquired traces. Build system can be probably re-created using CI/CD configs? What is easy?                               | 📝        |


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
