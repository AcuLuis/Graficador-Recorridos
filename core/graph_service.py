import json
from pathlib import Path
from typing import Any

from core.graph_model import GraphModel


class GraphService:
    @staticmethod
    def load_json(path: str | Path) -> GraphModel:
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as exc:
            raise ValueError(f"El archivo no es un JSON válido: {exc}") from exc

        GraphService.validate_graph_data(data)

        model = GraphModel()
        model.load_from_dict(data)
        return model

    @staticmethod
    def save_json(model: GraphModel, path: str | Path) -> None:
        payload = model.to_dict()
        with open(path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)

    @staticmethod
    def validate_graph_data(data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ValueError("El contenido del archivo no es un JSON válido para un grafo.")

        if "nodes" not in data or "edges" not in data:
            raise ValueError("El archivo JSON debe contener 'nodes' y 'edges'.")

        nodes = data["nodes"]
        edges = data["edges"]

        if not isinstance(nodes, list) or not isinstance(edges, list):
            raise ValueError("'nodes' y 'edges' deben ser listas.")

        for node in nodes:
            if not GraphService._is_int(node):
                raise ValueError(f"El nodo {node!r} no es válido: los IDs deben ser números enteros.")

        for edge in edges:
            if not isinstance(edge, list) or len(edge) not in (2, 3):
                raise ValueError(f"La arista {edge!r} debe tener la forma [origen, destino] o [origen, destino, {{datos}}].")
            if not GraphService._is_int(edge[0]) or not GraphService._is_int(edge[1]):
                raise ValueError(f"La arista {edge!r} debe unir nodos con IDs enteros.")
            if len(edge) == 3:
                if not isinstance(edge[2], dict):
                    raise ValueError(f"Los datos de la arista {edge!r} deben ser un objeto.")
                weight = edge[2].get("weight", 1)
                if isinstance(weight, bool) or not isinstance(weight, (int, float)):
                    raise ValueError(f"El peso de la arista {edge!r} debe ser numérico.")

        pos = data.get("pos", {})
        if not isinstance(pos, dict):
            raise ValueError("'pos' debe ser un objeto.")

        for key, value in pos.items():
            if (
                not isinstance(value, list)
                or len(value) != 2
                or not all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in value)
            ):
                raise ValueError(f"La posición del nodo {key} debe ser [x, y] numérico.")

    @staticmethod
    def _is_int(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)
