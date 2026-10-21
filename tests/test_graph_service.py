import json
import tempfile
import unittest
from pathlib import Path

from graph_service import GraphService

RAIZ = Path(__file__).resolve().parent.parent


class LoadJsonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def escribir(self, contenido: str) -> Path:
        path = Path(self.tmp.name) / "grafo.json"
        path.write_text(contenido, encoding="utf-8")
        return path

    def test_carga_grafo_de_prueba(self):
        model = GraphService.load_json(RAIZ / "datos_prueba.json")

        self.assertEqual(model.graph.number_of_nodes(), 8)
        self.assertEqual(model.graph.number_of_edges(), 17)
        self.assertEqual(model.graph_type, "Undirected")

    def test_json_mal_formado(self):
        path = self.escribir("{ esto no es json")

        with self.assertRaises(ValueError):
            GraphService.load_json(path)

    def test_faltan_claves(self):
        path = self.escribir(json.dumps({"nodes": [1, 2]}))

        with self.assertRaises(ValueError):
            GraphService.load_json(path)

    def test_arista_invalida(self):
        path = self.escribir(json.dumps({"nodes": [1, 2], "edges": [[1]]}))

        with self.assertRaises(ValueError):
            GraphService.load_json(path)

    def test_ids_no_enteros(self):
        path = self.escribir(json.dumps({"nodes": ["a"], "edges": []}))

        with self.assertRaises(ValueError):
            GraphService.load_json(path)

    def test_nodos_sin_posicion_reciben_una(self):
        path = self.escribir(json.dumps({
            "nodes": [1, 2, 3],
            "edges": [[1, 2], [2, 3, {"weight": 4}]],
            "graph_type": "Directed",
        }))

        model = GraphService.load_json(path)

        self.assertEqual(model.graph_type, "Directed")
        self.assertEqual(set(model.pos), {1, 2, 3})
        for x, y in model.pos.values():
            self.assertTrue(0 <= x <= 1 and 0 <= y <= 1)


if __name__ == "__main__":
    unittest.main()
