import ast
from typing import Any

import networkx as nx


class GraphModel:
    """Modelo centralizado para manejar un grafo, sus posiciones y metadatos visuales."""

    def __init__(self, graph_type: str = "Undirected"):
        self.graph_type = "Undirected"
        self.graph = nx.Graph()
        self.pos = {}
        self.edge_colors = {}
        self.edge_weights = {}
        self.set_graph_type(graph_type)

    def _normalize_graph_type(self, graph_type: str) -> str:
        aliases = {
            "Dirigido": "Directed",
            "Directed": "Directed",
            "NoDirigido": "Undirected",
            "Undirected": "Undirected",
        }
        return aliases.get(graph_type, "Undirected")

    def set_graph_type(self, graph_type: str) -> None:
        normalized_type = self._normalize_graph_type(graph_type)

        if normalized_type == "Directed":
            new_graph = nx.DiGraph()
        else:
            new_graph = nx.Graph()

        current_nodes = list(self.graph.nodes(data=True))
        current_edges = list(self.graph.edges(data=True))

        new_graph.add_nodes_from(current_nodes)
        for u, v, data in current_edges:
            new_graph.add_edge(u, v, **data)

        self.graph_type = normalized_type
        self.graph = new_graph

    def add_node(self, node_id: Any, position: tuple[float, float] | None = None) -> None:
        if node_id in self.graph.nodes:
            return

        self.graph.add_node(node_id)
        if position is not None:
            self.pos[node_id] = tuple(position)

    def add_edge(self, node1: Any, node2: Any, peso: int = 1) -> None:
        if node1 not in self.graph.nodes or node2 not in self.graph.nodes:
            raise ValueError(f"Los nodos {node1} y/o {node2} no existen en el grafo.")

        self.graph.add_edge(node1, node2, weight=peso)
        self.edge_colors[(node1, node2)] = "#2c3e50"
        self.edge_weights[(node1, node2)] = peso

        if not isinstance(self.graph, nx.DiGraph):
            self.edge_colors[(node2, node1)] = "#2c3e50"
            self.edge_weights[(node2, node1)] = peso

    def clear(self) -> None:
        if self.graph_type == "Directed":
            self.graph = nx.DiGraph()
        else:
            self.graph = nx.Graph()

        self.pos.clear()
        self.edge_colors.clear()
        self.edge_weights.clear()

    def set_node_position(self, node_id: Any, position: tuple[float, float]) -> None:
        if node_id not in self.graph.nodes:
            raise ValueError(f"El nodo {node_id} no existe.")

        self.pos[node_id] = tuple(position)

    def update_edge_weight(self, node1: Any, node2: Any, new_weight: int) -> None:
        if node1 not in self.graph.nodes or node2 not in self.graph.nodes:
            raise ValueError(f"Los nodos {node1} y/o {node2} no existen.")

        if not self.graph.has_edge(node1, node2):
            raise ValueError(f"La arista {node1} - {node2} no existe.")

        self.graph[node1][node2]["weight"] = new_weight
        self.edge_weights[(node1, node2)] = new_weight

        if not isinstance(self.graph, nx.DiGraph) and self.graph.has_edge(node2, node1):
            self.graph[node2][node1]["weight"] = new_weight
            self.edge_weights[(node2, node1)] = new_weight

    def eliminar_nodo(self, node_id: Any) -> None:
        if node_id not in self.graph.nodes:
            raise ValueError(f"El nodo {node_id} no existe.")

        self.graph.remove_node(node_id)
        self.pos.pop(node_id, None)

        edges_to_remove = [k for k in self.edge_colors if node_id in k]
        for edge in edges_to_remove:
            self.edge_colors.pop(edge, None)
            self.edge_weights.pop(edge, None)

    def eliminar_arista(self, node1: Any, node2: Any) -> None:
        if node1 not in self.graph.nodes or node2 not in self.graph.nodes:
            raise ValueError(f"Los nodos {node1} y/o {node2} no existen.")

        if self.graph.has_edge(node1, node2):
            self.graph.remove_edge(node1, node2)
            self.edge_colors.pop((node1, node2), None)
            self.edge_weights.pop((node1, node2), None)

        if not isinstance(self.graph, nx.DiGraph) and self.graph.has_edge(node2, node1):
            self.graph.remove_edge(node2, node1)
            self.edge_colors.pop((node2, node1), None)
            self.edge_weights.pop((node2, node1), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": list(self.graph.nodes()),
            "edges": [
                [u, v, dict(data)]
                for u, v, data in self.graph.edges(data=True)
            ],
            "pos": {str(k): v for k, v in self.pos.items()},
            "edge_colors": {str(k): v for k, v in self.edge_colors.items()},
            "edge_weights": {str(k): v for k, v in self.edge_weights.items()},
            "graph_type": self.graph_type,
        }

    def load_from_dict(self, data: dict[str, Any]) -> None:
        self.clear()

        graph_type = self._normalize_graph_type(data.get("graph_type", "Undirected"))
        self.graph_type = graph_type

        if graph_type == "Directed":
            self.graph = nx.DiGraph()
        else:
            self.graph = nx.Graph()

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        pos = data.get("pos", {})
        edge_colors = data.get("edge_colors", {})
        edge_weights = data.get("edge_weights", {})

        self.graph.add_nodes_from(nodes)

        for edge in edges:
            if len(edge) == 3:
                edge_data = edge[2]
                self.graph.add_edge(edge[0], edge[1], **edge_data)
            else:
                self.graph.add_edge(edge[0], edge[1])

        self.pos = {
            self._coerce_scalar_key(k): tuple(v)
            for k, v in pos.items()
        }
        self.edge_colors = {
            self._coerce_scalar_key(k): v
            for k, v in edge_colors.items()
        }
        self.edge_weights = {
            self._coerce_scalar_key(k): v
            for k, v in edge_weights.items()
        }

        for u, v in self.graph.edges():
            if (u, v) not in self.edge_weights:
                self.edge_weights[(u, v)] = self.graph.edges[u, v].get("weight", 1)

        self._assign_missing_positions()

    def _assign_missing_positions(self) -> None:
        """Ubica en el lienzo (0..1) los nodos que llegaron sin posición."""
        missing = [node for node in self.graph.nodes() if node not in self.pos]
        if not missing:
            return

        layout = nx.spring_layout(self.graph, seed=42)
        xs = [p[0] for p in layout.values()]
        ys = [p[1] for p in layout.values()]
        span_x = (max(xs) - min(xs)) or 1
        span_y = (max(ys) - min(ys)) or 1

        for node in missing:
            x, y = layout[node]
            self.pos[node] = (
                0.1 + 0.8 * (x - min(xs)) / span_x,
                0.1 + 0.8 * (y - min(ys)) / span_y,
            )

    def _coerce_scalar_key(self, key: Any) -> Any:
        if isinstance(key, str):
            try:
                return ast.literal_eval(key)
            except Exception:
                return key
        return key
