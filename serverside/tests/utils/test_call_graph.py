import json
from pathlib import Path

import pytest

from src.utils.call_graph import CallGraph


@pytest.fixture
def sample_trace():
    trace_path = Path(__file__).parent.parent / "assets" / "sample_trace.json"
    with open(trace_path) as f:
        return json.load(f)


def test_call_graph_build(sample_trace):
    call_graph = CallGraph(json.dumps(sample_trace))

    assert call_graph.graph.number_of_nodes() > 0
    assert call_graph.graph.number_of_edges() > 0

    # Assert specific function presence and properties
    function_nodes = call_graph.find_node_by_fname("calculate_avg")
    assert function_nodes

    for node_id in function_nodes:
        node = call_graph.graph.nodes[node_id]
        assert node["function"] == "calculate_avg"
        assert "arguments" in node
        assert "return_value" in node


def test_call_graph_build_and_tags(sample_trace):
    call_graph = CallGraph(json.dumps(sample_trace))

    assert call_graph.graph.number_of_nodes() > 0
    assert call_graph.graph.number_of_edges() > 0

    internal_nodes = call_graph.find_node_by_fname("calculate_avg")
    stdlib_nodes = call_graph.find_node_by_fname("iscoroutinefunction")

    # Ensure we found the nodes
    assert internal_nodes
    assert stdlib_nodes

    # Check we are able to differentiate between INTERNAL (interesting modules) and LIB modules (not-so-interesting)
    for node_id in internal_nodes:
        node = call_graph.graph.nodes[node_id]
        assert node["tag"] == "INTERNAL", f"Node {node_id} expected to be INTERNAL, got {node['tag']}"

    for node_id in stdlib_nodes:
        node = call_graph.graph.nodes[node_id]
        assert node["tag"] == "STDLIB", f"Node {node_id} expected to be STDLIB, got {node['tag']}"
