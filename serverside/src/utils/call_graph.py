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

        for event in data['execution_trace']:
            if event['event'] == 'call':
                # Create a node attribute dictionary directly
                node_attrs = {
                    "function": event['function'],
                    "file_line": f"{event['file']}:{event['line']}",
                    "tag": event.get('tag', ["INTERNAL"]),
                    "arguments": event.get('arguments', {}),  # Added arguments
                    "return_value": event.get('return_value', {}),  # Placeholder for return value, to be updated on 'return' event
                }
                self.graph.add_node(event['id'], **node_attrs)

                # Add an edge from the caller to the current function call
                caller_id = event.get('caller_id')
                if caller_id and caller_id in self.graph:
                    self.graph.add_edge(caller_id, event['id'])

    def iterate_graph(self) -> None:
        """Iterates through the graph, printing details of each node and its successors."""
        for node, attrs in self.graph.nodes(data=True):
            function_name = attrs['function']
            file_line = attrs['file_line']
            tag = attrs['tag']
            successors = ", ".join(self.graph.nodes[succ]['function'] for succ in self.graph.successors(node))
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
            if attrs['function'] == function_name:
                matching_nodes.append(node)
        return matching_nodes

    def __repr__(self) -> str:
        """Generates a string representation of the call graph."""
        summary = f"CallGraph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges\n"
        detailed_view = "Sample connections:\n"
        for i, (node, data) in enumerate(self.graph.nodes(data=True)):
            if i >= 100:  # Limit the number of nodes displayed
                detailed_view += "...\n"
                break
            function_name = data['function']
            file_line = data['file_line']
            tag = data['tag']
            successors = ", ".join(self.graph.nodes[succ]['function'] for succ in self.graph.successors(node))
            detailed_view += f"  {function_name} ({file_line}, {tag}) -> {successors or 'No outgoing calls'}\n"

        return summary + detailed_view