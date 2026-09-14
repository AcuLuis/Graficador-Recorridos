import json
from pathlib import Path
from typing import Any

from graph_model import GraphModel


class GraphService:
    @staticmethod
    def load_json(path: str | Path) -> GraphModel:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

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
