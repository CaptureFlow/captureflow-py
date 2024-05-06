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
        
        # After building the graph, calculate descendants for all nodes
        for node in list(self.graph.nodes):
            self._calculate_descendants(node)

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
    
    def compress_graph(self):
        changes_made = True
        while changes_made:
            changes_made = False
            node_depths = self._calculate_depths()  # Recalculate depths on each iteration
            print("NODE DEPTHS = ", node_depths)
            nodes_by_depth = sorted(self.graph.nodes(), key=lambda n: node_depths.get(n, 0), reverse=True)

            for node in nodes_by_depth:
                if self.graph.has_node(node) and self.graph.nodes[node].get('total_children_count', 0) > 50:
                    # Remove this node's children
                    children = list(self.graph.successors(node))
                    for child in children:
                        self._remove_descendants(child)

                    self.graph.nodes[node]['total_children_count'] = 0
                    self.graph.nodes[node]['is_node_compressed'] = True  # Mark this node as compressed
                    changes_made = True  # Indicate changes for another pass

            # changes_made = False

            # Recalculate descendants at the end of each full pass
                    for node in self.graph.nodes():
                        self._calculate_descendants(node)

    def _remove_descendants(self, node):
        """Recursively remove a node and all its descendants from the graph."""
        # List all children (successors) of the node
        children = list(self.graph.successors(node))
        for child in children:
            self._remove_descendants(child)  # Recursively remove each child

        # After all children are removed, remove the node itself
        self.graph.remove_node(node)


    def _calculate_depths(self):
        """Calculate depth for each node based on the longest path to any leaf."""
        node_depths = {}
        # Ensure calculation respects topological order
        try:
            for node in nx.topological_sort(self.graph):  # Ensures we calculate from leaves to root
                if not list(self.graph.predecessors(node)):  # If no children, depth is 0
                    node_depths[node] = 0
                    self.graph.nodes[node]['depth'] = 0
                else:
                    # Only consider children that are still in the graph
                    # node_depths[node] = max((node_depths[child] + 1 for child in self.graph.successors(node) if child in node_depths), default=0)
                    node_depths[node] = max((node_depths[child] + 1 for child in self.graph.predecessors(node) if child in node_depths), default=0)
                    self.graph.nodes[node]['depth'] = node_depths[node]
        except nx.NetworkXError as e:
            logger.error(f"Failed to calculate depths, possibly due to cyclic dependency: {e}")
            return {}
        return node_depths

    def _calculate_descendants(self, node):
        """Recalculate the total number of descendants for each node."""
        if not list(self.graph.successors(node)):  # If no children
            self.graph.nodes[node]['total_children_count'] = 0
            return 0
        total_count = 0
        for successor in self.graph.successors(node):
            child_count = self._calculate_descendants(successor)
            total_count += child_count + 1
        self.graph.nodes[node]['total_children_count'] = total_count
        return total_count

    def draw(self, output_filename="func_call_graph", compressed=False):
        from graphviz import Digraph

        dot = Digraph(comment="Function Call Graph")
        color_mapping = {"STDLIB": "gray", "LIBRARY": "blue", "INTERNAL": "white"}
        compressed_color = "lightgrey"  # Color for compressed nodes

        if compressed:
            self.compress_graph()  # Compress the graph before drawing

        nodes = [(node, self.graph.nodes[node]) for node in self.graph.nodes()]
        edges = list(self.graph.edges())

        for node, attrs in nodes:
            tag = attrs["tag"]
            node_color = color_mapping.get("EXCEPTION" if attrs["exception"] else tag, "white")

            if attrs.get('is_node_compressed', False):
                node_color = compressed_color  # Use special color for compressed nodes
            else:
                node_color = color_mapping.get(tag, "white")  # Use default colors for tags

            label_parts = [
                f"Function: {attrs['function']}",
                f"Tag: {tag}",
                f"Total Children Count: {attrs['total_children_count']}",
                f"Depth = {attrs['depth']}",
                f"Compression Status: {'Compressed' if attrs.get('is_node_compressed', False) else 'Not Compressed'}",
                # f"Arguments: {json.dumps(attrs.get('arguments', {}), indent=2)}",
                # f"Returns: {json.dumps(attrs.get('return_value', {}), indent=2)}",
                f"Did Raise: {attrs.get('did_raise', {})}",
                f"Traceback: {attrs.get('unhandled_exception', {})}",
            ]

            dot.node(node, label="\n".join(label_parts), style="filled", fillcolor=node_color)

        for u, v in edges:
            dot.edge(u, v)

        dot.render(output_filename, view=True)


if __name__ == "__main__":
    log_file_path = "/Users/nikitakutc/projects/captureflow-py/serverside/trace_33c73b42-bf7c-4196-bdd8-048049edff00.json"
    # log_file_path = "/Users/nikitakutc/projects/captureflow-py/serverside/tests/assets/sample_trace.json"
    with open(log_file_path, "r") as file:
        log_data = file.read()

    call_graph = CallGraph(log_data)
    call_graph.draw(compressed=True)
    print(f"Generated call graph has been saved.")
