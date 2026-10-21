import unittest

import networkx as nx

from algorithms_service import AlgorithmsService


def grafo_cadena():
    graph = nx.Graph()
    graph.add_edge(1, 2, weight=1)
    graph.add_edge(2, 3, weight=1)
    graph.add_edge(1, 4, weight=1)
    return graph


class BfsTests(unittest.TestCase):
    def test_recorre_por_niveles(self):
        result = AlgorithmsService.bfs(grafo_cadena(), 1)

        self.assertEqual(result["aristas"], [(1, 2), (1, 4), (2, 3)])

    def test_nodo_inexistente(self):
        result = AlgorithmsService.bfs(grafo_cadena(), 99)

        self.assertEqual(result["aristas"], [])
        self.assertIn("no existe", result["content"])


class DfsTests(unittest.TestCase):
    def test_recorre_en_profundidad(self):
        result = AlgorithmsService.dfs(grafo_cadena(), 1)

        self.assertEqual(result["aristas"], [(1, 2), (2, 3), (1, 4)])
        self.assertIn("Va de nodo 2 -> nodo 3", result["content"])

    def test_nodo_inexistente(self):
        result = AlgorithmsService.dfs(grafo_cadena(), 99)

        self.assertEqual(result["aristas"], [])


class KruskalTests(unittest.TestCase):
    def test_arbol_minimo(self):
        graph = nx.Graph()
        graph.add_edge(1, 2, weight=4)
        graph.add_edge(2, 3, weight=1)
        graph.add_edge(1, 3, weight=2)

        result = AlgorithmsService.kruskal(graph)

        self.assertEqual(result["aristas"], [(2, 3), (1, 3)])
        self.assertIn("Peso total del MST: 3", result["content"])


class DijkstraTests(unittest.TestCase):
    def test_distancias_minimas(self):
        graph = nx.Graph()
        graph.add_edge(1, 2, weight=10)
        graph.add_edge(1, 3, weight=1)
        graph.add_edge(3, 2, weight=2)
        graph.add_node(4)

        result = AlgorithmsService.dijkstra(graph, 1)

        self.assertCountEqual(result["aristas"], [(1, 3), (3, 2)])
        self.assertIn("Nodo 2: 3", result["content"])
        self.assertIn("Nodo 4: Inalcanzable", result["content"])

    def test_respeta_direccion(self):
        graph = nx.DiGraph()
        graph.add_edge(2, 1, weight=1)

        result = AlgorithmsService.dijkstra(graph, 1)

        self.assertEqual(result["aristas"], [])
        self.assertIn("Nodo 2: Inalcanzable", result["content"])


if __name__ == "__main__":
    unittest.main()
