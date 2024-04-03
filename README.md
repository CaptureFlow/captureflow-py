# captureflow-py

Leverage LLMs for maintaining and improving your existing repositories. Software maintenance consumes a significant portion of dev time, yet **deployed applications are already rich with embedded context**.

By utilizing traces from production applications, we can unlock new approaches for automated bug fixes in response to exceptions. For an example, see this [MR](https://github.com/CaptureFlow/captureflow-py/pull/21) and [sample verbose trace](https://gist.github.com/NickKuts/f390d377906aa666cd759232b0d8ed43).

**NOTE:** This is not yet ready for production use and it will degrade your application's performance. It presents an end-to-end pipeline that can be optimized by balancing tracing verbosity with the impact it can provide. For more details, check the [clientside/README](https://github.com/CaptureFlow/captureflow-py/blob/main/clientside/README.md).


## Main components

![Alt text](./assets/main-chart.svg)

Integrate our tracing tool into your application to capture and send execution traces to the server. When traces contain unhandled exceptions, the server analyzes them and automatically generates MR accompanied by a change reasoning.

**Support is currently limited to Python, OpenAI, and GitHub.**

## Roadmap / Current Status

- [x] **Pipeline Setup**: Implement an end-to-end pipeline including tracer and server. The tracer outputs JSONs for Python execution frames, and the server stores traces, enriching them with GitHub metadata.
- [x] **MR Generation Heuristic**: Focused on methods as the unit of optimization for the initial heuristic approach to generating Merge Requests.
- [x] **Automated Code Fixes**: Utilizes exception traces and execution context for proposing targeted fixes for exceptions.
- [ ] **Benchmarking & Testing**:
    - [x] More sophisticated benchmarking scenarios are under development.
- [ ] **Test Case Extension**: Extend existing test cases using accumulated trace data for more realistic mock data and scenarios.
- [ ] **RAG Pipeline Improvement**: Enhance the Retrieve and Generate (RAG) pipeline with similar module fetching from code embeddings, ctags implementation, and standardized code parsing methods.



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
