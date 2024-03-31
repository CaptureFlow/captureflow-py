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
        data = json.loads(log_data) if isinstance(log_data, str) else log_data
        # Track nodes that threw exceptions
        exception_nodes = {}

        for event in data["execution_trace"]:
            if event["event"] in ["call", "exception"]:
                if event["event"] == "call":
                    node_attrs = {
                        "function": event["function"],
                        "file_line": f"{event['file']}:{event['line']}",
                        "tag": event.get("tag", "INTERNAL"),
                        "arguments": event.get("arguments", {}),
                        "return_value": event.get("return_value", {}),
                        "exception": False,  # Initialize nodes with no exception
                    }
                elif event["event"] == "exception":
                    # Update the caller node with exception info
                    caller_node = self.graph.nodes[event["caller_id"]]
                    caller_node["did_raise"] = True
                    caller_node["unhandled_exception"] = {
                        "type": event["exception_info"]["type"],
                        "value": event["exception_info"]["value"],
                        "traceback": event["exception_info"]["traceback"],
                    }

                    continue

                self.graph.add_node(event["id"], **node_attrs)

                # Add an edge from the caller to the current function call
                caller_id = event.get("caller_id")
                if caller_id and caller_id in self.graph:
                    self.graph.add_edge(caller_id, event["id"])

                # If the caller had an exception, link this event as part of the exception chain
                if caller_id in exception_nodes:
                    self.graph.add_edge(exception_nodes[caller_id], event["id"])

    def iterate_graph(self) -> None:
        """Iterates through the graph, printing details of each node and its successors."""
        for node, attrs in self.graph.nodes(data=True):
            function_name = attrs["function"]
            file_line = attrs["file_line"]
            tag = attrs["tag"]
            successors = ", ".join(self.graph.nodes[succ]["function"] for succ in self.graph.successors(node))
            logging.info(f"Function: {function_name} ({file_line}, {tag}) -> {successors or 'No outgoing calls'}")

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
            tag = attrs["tag"]
            node_color = color_mapping.get("EXCEPTION" if attrs["exception"] else tag, "white")

            label_parts = [
                f"Function: {attrs['function']}",
                f"Tag: {tag}",
                f"Arguments: {json.dumps(attrs.get('arguments', {}), indent=2)}",
                f"Returns: {json.dumps(attrs.get('return_value', {}), indent=2)}",
                f"Did Raise: {attrs.get('did_raise', {})}",
                f"Traceback: {attrs.get('unhandled_exception', {})}",
            ]

            dot.node(node, label="\n".join(label_parts), style="filled", fillcolor=node_color)

        for u, v in edges:
            dot.edge(u, v)

        dot.render(output_filename, view=True)


if __name__ == "__main__":
    log_file_path = "/Users/nikitakutc/projects/captureflow-py/serverside/tests/assets/sample_trace_with_exception.json"
    # log_file_path = "/Users/nikitakutc/projects/captureflow-py/serverside/tests/assets/sample_trace.json"
    with open(log_file_path, "r") as file:
        log_data = file.read()

    call_graph = CallGraph(log_data)
    call_graph.draw()
    print(f"Generated call graph has been saved.")
