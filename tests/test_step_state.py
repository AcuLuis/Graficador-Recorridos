import unittest

import networkx as nx

from core import step_state as st
from core.algorithms import AlgorithmsService


def grafo_cadena():
    graph = nx.Graph()
    graph.add_edge(1, 2, weight=1)
    graph.add_edge(2, 3, weight=1)
    graph.add_edge(1, 4, weight=1)
    return graph


class BfsPasoAPasoTests(unittest.TestCase):
    def setUp(self):
        self.res = AlgorithmsService.bfs(grafo_cadena(), 1)

    def estado(self, k):
        return st.estado_hasta(self.res["pasos"], k, self.res["aristas"])

    def test_sin_pasos_aplicados_todo_pendiente(self):
        estado = self.estado(0)

        self.assertEqual(estado.nodos, {})
        self.assertTrue(estado.usa_estados_de_nodo)
        self.assertIsNone(estado.paso)
        self.assertFalse(estado.final)

    def test_primer_paso_visita_el_inicio(self):
        self.assertEqual(self.estado(1).nodos, {1: st.ACTUAL})

    def test_descubrir_pone_en_espera(self):
        estado = self.estado(3)  # visita 1, descubre 2 y 4

        self.assertEqual(estado.nodos, {1: st.ACTUAL, 2: st.FRONTERA, 4: st.FRONTERA})
        self.assertEqual(estado.estado_arista(2, 1), st.ARBOL)

    def test_visitar_el_siguiente_marca_visitado_el_anterior(self):
        estado = self.estado(4)  # visita 2

        self.assertEqual(estado.nodos[1], st.VISITADO)
        self.assertEqual(estado.nodos[2], st.ACTUAL)

    def test_estado_final_muestra_resultado(self):
        estado = self.estado(len(self.res["pasos"]))

        self.assertTrue(estado.final)
        self.assertEqual(set(estado.nodos.values()), {st.VISITADO})
        self.assertEqual(
            {clave for clave, valor in estado.aristas.items() if valor == st.RESULTADO},
            {(1, 2), (1, 4), (2, 3)},
        )

    def test_k_fuera_de_rango_se_acota(self):
        self.assertTrue(self.estado(999).final)
        self.assertEqual(self.estado(-5).nodos, {})


class DfsPasoAPasoTests(unittest.TestCase):
    def test_avanzar_y_finalizar(self):
        res = AlgorithmsService.dfs(grafo_cadena(), 1)
        pasos = res["pasos"]
        # 1 visitar, 2 avanzar a 2, 3 avanzar a 3, 4 finalizar 3
        estado = st.estado_hasta(pasos, 4)

        self.assertEqual(estado.nodos, {1: st.VISITADO, 2: st.VISITADO, 3: st.FINALIZADO})
        self.assertEqual(estado.estado_arista(2, 3), st.ARBOL)

    def test_aristas_de_retroceso_persisten_en_el_final(self):
        graph = nx.cycle_graph([1, 2, 3])
        res = AlgorithmsService.dfs(graph, 1)

        final = st.estado_hasta(res["pasos"], len(res["pasos"]), res["aristas"])

        self.assertEqual(final.estado_arista(1, 3), st.NO_ARBOL)
        self.assertEqual(final.estado_arista(1, 2), st.RESULTADO)


class DijkstraPasoAPasoTests(unittest.TestCase):
    def test_solo_la_mejor_candidata_hacia_cada_nodo(self):
        graph = nx.Graph()
        graph.add_edge(1, 2, weight=10)
        graph.add_edge(1, 3, weight=1)
        graph.add_edge(3, 2, weight=2)
        res = AlgorithmsService.dijkstra(graph, 1)

        # Tras procesar el nodo 3, la mejor forma de llegar a 2 es vía 3.
        indice = next(i for i, paso in enumerate(res["pasos"]) if paso.arista == (3, 2)) + 1
        estado = st.estado_hasta(res["pasos"], indice)

        self.assertEqual(estado.estado_arista(3, 2), st.CANDIDATA)
        self.assertIsNone(estado.estado_arista(1, 2))


class KruskalPasoAPasoTests(unittest.TestCase):
    def test_descartadas_se_mantienen_en_el_final(self):
        graph = nx.Graph()
        graph.add_weighted_edges_from([(1, 2, 4), (2, 3, 1), (1, 3, 2)])
        res = AlgorithmsService.kruskal(graph)

        final = st.estado_hasta(res["pasos"], len(res["pasos"]), res["aristas"])

        self.assertEqual(final.estado_arista(1, 2), st.DESCARTADA)
        self.assertEqual(final.estado_arista(2, 3), st.RESULTADO)


class SinPasosTests(unittest.TestCase):
    def test_resultado_sin_pasos_no_usa_estados_de_nodo(self):
        graph = nx.DiGraph([(1, 2), (2, 1)])
        res = AlgorithmsService.componentes_fuertes(graph)

        estado = st.estado_hasta(res["pasos"], 0, res["aristas"], dirigido=True)

        self.assertTrue(estado.final)
        self.assertFalse(estado.usa_estados_de_nodo)
        self.assertEqual(estado.estado_arista(2, 1), st.RESULTADO)


if __name__ == "__main__":
    unittest.main()
