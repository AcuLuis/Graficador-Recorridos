import unittest

import networkx as nx

from core.algorithms import AlgorithmsService, Paso


def grafo_cadena():
    graph = nx.Graph()
    graph.add_edge(1, 2, weight=1)
    graph.add_edge(2, 3, weight=1)
    graph.add_edge(1, 4, weight=1)
    return graph


def dirigido(*aristas, pesos=None):
    graph = nx.DiGraph()
    for i, (u, v) in enumerate(aristas):
        graph.add_edge(u, v, weight=pesos[i] if pesos else 1)
    return graph


class BfsTests(unittest.TestCase):
    def test_recorre_por_niveles(self):
        result = AlgorithmsService.bfs(grafo_cadena(), 1)

        self.assertEqual(result["aristas"], [(1, 2), (1, 4), (2, 3)])
        self.assertEqual(result["orden"], [1, 2, 4, 3])
        self.assertEqual(result["niveles"], {1: 0, 2: 1, 4: 1, 3: 2})

    def test_vecinos_en_orden_ascendente(self):
        graph = nx.Graph()
        graph.add_edges_from([(1, 9), (1, 3), (1, 5)])

        self.assertEqual(AlgorithmsService.bfs(graph, 1)["orden"], [1, 3, 5, 9])

    def test_informa_no_alcanzados(self):
        graph = grafo_cadena()
        graph.add_node(7)

        self.assertIn("No alcanzados desde 1: 7", AlgorithmsService.bfs(graph, 1)["content"])

    def test_pasos_estructurados(self):
        pasos = AlgorithmsService.bfs(grafo_cadena(), 1)["pasos"]

        self.assertIsInstance(pasos[0], Paso)
        self.assertEqual(pasos[0].tipo, "visitar")
        self.assertEqual(pasos[1].arista, (1, 2))

    def test_nodo_inexistente(self):
        with self.assertRaises(ValueError):
            AlgorithmsService.bfs(grafo_cadena(), 99)


class DfsTests(unittest.TestCase):
    def test_recorre_en_profundidad(self):
        result = AlgorithmsService.dfs(grafo_cadena(), 1)

        self.assertEqual(result["aristas"], [(1, 2), (2, 3), (1, 4)])
        self.assertIn("Va de nodo 2 -> nodo 3", result["content"])

    def test_tiempos_de_descubrimiento_y_finalizacion(self):
        result = AlgorithmsService.dfs(grafo_cadena(), 1)

        self.assertEqual(result["descubrimiento"], {1: 1, 2: 2, 3: 3, 4: 6})
        self.assertEqual(result["finalizacion"], {3: 4, 2: 5, 4: 7, 1: 8})

    def test_no_dirigido_detecta_retroceso(self):
        graph = nx.cycle_graph([1, 2, 3])

        result = AlgorithmsService.dfs(graph, 1)

        self.assertEqual(result["clasificacion"]["retroceso"], [(3, 1)])
        self.assertIn("ciclo", result["content"])

    def test_dirigido_clasifica_avance_y_cruce(self):
        graph = dirigido((1, 2), (2, 3), (1, 3), (1, 4), (4, 3), (3, 1))

        clases = AlgorithmsService.dfs(graph, 1)["clasificacion"]

        self.assertEqual(clases["arbol"], [(1, 2), (2, 3), (1, 4)])
        self.assertEqual(clases["retroceso"], [(3, 1)])
        self.assertEqual(clases["avance"], [(1, 3)])
        self.assertEqual(clases["cruce"], [(4, 3)])

    def test_grafo_grande_no_desborda_la_pila(self):
        graph = nx.path_graph(5000)

        self.assertEqual(len(AlgorithmsService.dfs(graph, 0)["aristas"]), 4999)

    def test_nodo_inexistente(self):
        with self.assertRaises(ValueError):
            AlgorithmsService.dfs(grafo_cadena(), 99)


class DijkstraTests(unittest.TestCase):
    def grafo(self):
        graph = nx.Graph()
        graph.add_edge(1, 2, weight=10)
        graph.add_edge(1, 3, weight=1)
        graph.add_edge(3, 2, weight=2)
        graph.add_node(4)
        return graph

    def test_distancias_minimas(self):
        result = AlgorithmsService.dijkstra(self.grafo(), 1)

        self.assertCountEqual(result["aristas"], [(1, 3), (3, 2)])
        self.assertEqual(result["distancias"][2], 3)
        self.assertIn("Nodo 2: 3", result["content"])
        self.assertIn("Nodo 4: Inalcanzable", result["content"])

    def test_camino_a_destino(self):
        result = AlgorithmsService.dijkstra(self.grafo(), 1, destino=2)

        self.assertEqual(result["aristas"], [(1, 3), (3, 2)])
        self.assertIn("Camino más corto de 1 a 2: 1 → 3 → 2 (costo 3)", result["content"])

    def test_destino_inalcanzable(self):
        result = AlgorithmsService.dijkstra(self.grafo(), 1, destino=4)

        self.assertEqual(result["aristas"], [])
        self.assertIn("No existe camino de 1 a 4", result["content"])

    def test_respeta_direccion(self):
        result = AlgorithmsService.dijkstra(dirigido((2, 1)), 1)

        self.assertEqual(result["aristas"], [])
        self.assertIn("Nodo 2: Inalcanzable", result["content"])

    def test_rechaza_pesos_negativos(self):
        with self.assertRaisesRegex(ValueError, "Bellman-Ford"):
            AlgorithmsService.dijkstra(dirigido((1, 2), pesos=[-3]), 1)

    def test_destino_inexistente(self):
        with self.assertRaises(ValueError):
            AlgorithmsService.dijkstra(self.grafo(), 1, destino=99)


class BellmanFordTests(unittest.TestCase):
    def test_pesos_negativos_sin_ciclo(self):
        graph = dirigido((1, 2), (1, 3), (3, 2), pesos=[4, 2, -3])

        result = AlgorithmsService.bellman_ford(graph, 1)

        self.assertEqual(result["distancias"], {1: 0, 2: -1, 3: 2})
        self.assertEqual(result["caminos"][2], [1, 3, 2])

    def test_detecta_ciclo_negativo(self):
        graph = dirigido((1, 2), (2, 3), (3, 2), pesos=[1, -2, 1])

        result = AlgorithmsService.bellman_ford(graph, 1)

        self.assertIn("ciclo de peso negativo", result["content"])
        self.assertEqual(set(result["ciclo_negativo"]), {2, 3})
        self.assertEqual(result["ciclo_negativo"][0], result["ciclo_negativo"][-1])

    def test_no_dirigido_con_arista_negativa(self):
        graph = nx.Graph()
        graph.add_edge(1, 2, weight=-1)

        result = AlgorithmsService.bellman_ford(graph, 1)

        self.assertIn("ciclo_negativo", result)

    def test_coincide_con_dijkstra_sin_negativos(self):
        graph = nx.Graph()
        graph.add_weighted_edges_from([(1, 2, 7), (1, 3, 9), (2, 3, 1), (3, 4, 2), (2, 4, 15)])

        self.assertEqual(
            AlgorithmsService.bellman_ford(graph, 1)["distancias"],
            AlgorithmsService.dijkstra(graph, 1)["distancias"],
        )


class ArbolMinimoTests(unittest.TestCase):
    def triangulo(self):
        graph = nx.Graph()
        graph.add_edge(1, 2, weight=4)
        graph.add_edge(2, 3, weight=1)
        graph.add_edge(1, 3, weight=2)
        return graph

    def test_kruskal(self):
        result = AlgorithmsService.kruskal(self.triangulo())

        self.assertEqual(result["aristas"], [(2, 3), (1, 3)])
        self.assertEqual(result["descartadas"], [(1, 2)])
        self.assertIn("Peso total del MST: 3", result["content"])

    def test_prim(self):
        result = AlgorithmsService.prim(self.triangulo(), inicio=1)

        self.assertEqual(result["aristas"], [(1, 3), (3, 2)])
        self.assertEqual(result["peso_total"], 3)

    def test_kruskal_y_prim_dan_el_mismo_peso(self):
        graph = nx.Graph()
        graph.add_weighted_edges_from([
            (1, 2, 10), (1, 7, 9), (2, 4, 5), (4, 7, 7), (1, 5, 14), (5, 6, 12),
            (1, 8, 3), (8, 6, 15), (4, 8, 9), (4, 6, 1), (3, 6, 4), (3, 8, 6),
        ])

        self.assertEqual(
            AlgorithmsService.kruskal(graph)["peso_total"],
            AlgorithmsService.prim(graph)["peso_total"],
        )

    def test_grafo_disconexo_produce_bosque(self):
        graph = self.triangulo()
        graph.add_edge(8, 9, weight=5)

        for algoritmo in (AlgorithmsService.kruskal, AlgorithmsService.prim):
            result = algoritmo(graph)
            self.assertEqual(len(result["aristas"]), 3)
            self.assertIn("bosque de 2 árboles", result["content"])

    def test_rechaza_dirigidos(self):
        for algoritmo in (AlgorithmsService.kruskal, AlgorithmsService.prim):
            with self.assertRaises(ValueError):
                algoritmo(dirigido((1, 2)))


class AnalisisTests(unittest.TestCase):
    def test_orden_topologico(self):
        graph = dirigido((5, 1), (1, 3), (2, 3), (3, 4))

        self.assertEqual(AlgorithmsService.orden_topologico(graph)["orden"], [2, 5, 1, 3, 4])

    def test_orden_topologico_con_ciclo(self):
        graph = dirigido((1, 2), (2, 3), (3, 2))

        result = AlgorithmsService.orden_topologico(graph)

        self.assertIsNone(result["orden"])
        self.assertIn("no admite orden topológico", result["content"])

    def test_orden_topologico_requiere_dirigido(self):
        with self.assertRaises(ValueError):
            AlgorithmsService.orden_topologico(grafo_cadena())

    def test_detectar_ciclo(self):
        result = AlgorithmsService.detectar_ciclo(dirigido((1, 2), (2, 3), (3, 1)))

        self.assertEqual(len(result["aristas"]), 3)
        self.assertEqual(result["ciclo"][0], result["ciclo"][-1])

    def test_sin_ciclos(self):
        result = AlgorithmsService.detectar_ciclo(grafo_cadena())

        self.assertIsNone(result["ciclo"])
        self.assertIn("bosque", result["content"])

    def test_componentes_fuertes(self):
        graph = dirigido((1, 2), (2, 1), (2, 3), (3, 4), (4, 3))
        graph.add_node(5)

        result = AlgorithmsService.componentes_fuertes(graph)

        self.assertEqual(result["componentes"], [[1, 2], [3, 4], [5]])
        self.assertCountEqual(result["aristas"], [(1, 2), (2, 1), (3, 4), (4, 3)])


if __name__ == "__main__":
    unittest.main()
