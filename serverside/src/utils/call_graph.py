import json
import logging

import networkx as nx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CallGraph:
    def __init__(self, log_data: str):
        self.graph = nx.DiGraph()
        self._build_graph(log_data)

    def _build_graph(self, log_data: str) -> None:
        """Builds the call graph from the provided log data."""
        data = json.loads(log_data) if isinstance(log_data, str) else log_data

        for event in data["execution_trace"]:
            if event["event"] == "call":
                node_attrs = {
                    "function": event["function"],
                    "file_line": f"{event['file']}:{event['line']}",
                    "tag": event.get("tag", ["INTERNAL"]),
                    "arguments": event.get("arguments", {}),
                    "return_value": event.get("return_value", {}),
                }
                self.graph.add_node(event["id"], **node_attrs)

                # Add an edge from the caller to the current function call
                caller_id = event.get("caller_id")
                if caller_id and caller_id in self.graph:
                    self.graph.add_edge(caller_id, event["id"])

    def iterate_graph(self) -> None:
        """Iterates through the graph, printing details of each node and its successors."""
        for node, attrs in self.graph.nodes(data=True):
            function_name = attrs["function"]
            file_line = attrs["file_line"]
            tag = attrs["tag"]
            successors = ", ".join(
                self.graph.nodes[succ]["function"]
                for succ in self.graph.successors(node)
            )
            logging.info(
                f"Function: {function_name} ({file_line}, {tag}) -> {successors or 'No outgoing calls'}"
            )

    def export_for_graphviz(self) -> None:
        """Exports the graph in a format compatible with Graphviz."""
        nodes = [(node, self.graph.nodes[node]) for node in self.graph.nodes()]
        edges = list(self.graph.edges())
        return nodes, edges

    def find_node_by_fname(self, function_name: str) -> list[any]:
        """Finds nodes that correspond to a given function name."""
        matching_nodes = []
        for node, attrs in self.graph.nodes(data=True):
            if attrs["function"] == function_name:
                matching_nodes.append(node)
        return matching_nodes

    def draw(self, output_filename="func_call_graph"):
        from graphviz import Digraph

        dot = Digraph(comment="Function Call Graph")
        color_mapping = {"STDLIB": "gray", "LIBRARY": "blue", "INTERNAL": "white"}

        nodes = [(node, self.graph.nodes[node]) for node in self.graph.nodes()]
        edges = list(self.graph.edges())

        for node, attrs in nodes:
            func_name = attrs["function"]
            tag = attrs["tag"]
            file_line = attrs["file_line"]
            arguments = attrs["arguments"]
            return_value = attrs["return_value"]
            node_color = color_mapping.get(tag, "white")

            label = f"{func_name}\n{file_line}\n[{tag}]\nInput:{arguments}\nReturns:{return_value}"
            dot.node(node, label=label, style="filled", fillcolor=node_color)

        for u, v in edges:
            dot.edge(u, v)

        dot.render("func_call_graph", view=True)

        return dot


if __name__ == "__main__":
    log_file_path = "/Users/nikitakutc/projects/captureflow-py/serverside/tests/assets/sample_trace_with_exception.json"
    with open(log_file_path, "r") as file:
        log_data = file.read()

    call_graph = CallGraph(log_data)
    call_graph.draw()
    print(f"Generated call graph has been saved.")
