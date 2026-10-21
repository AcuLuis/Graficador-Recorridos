"""Algoritmos sobre grafos con registro de pasos para visualización.

Cada algoritmo devuelve un diccionario con al menos:
  - "aristas": aristas a resaltar en el lienzo.
  - "pasos": lista de Paso en el orden en que ocurrieron.
  - "content": explicación legible (pasos + resumen).
Las entradas inválidas se informan con ValueError.
"""
import heapq
from collections import deque
from dataclasses import dataclass
from typing import Any

import networkx as nx

INFINITO = float("inf")


@dataclass(frozen=True)
class Paso:
    tipo: str
    texto: str
    nodo: Any = None
    arista: tuple | None = None


def _vecinos(graph, node):
    """Vecinos en orden ascendente, para que el recorrido sea predecible."""
    return sorted(graph.neighbors(node))


def _validar_nodo(graph, node, rol="inicial"):
    if node not in graph:
        raise ValueError(f"El nodo {rol} {node} no existe.")


def _peso(graph, u, v):
    return graph.edges[u, v].get("weight", 1)


def _fmt_dist(distancia):
    return "Inalcanzable" if distancia == INFINITO else f"{distancia:g}"


def _fmt_camino(camino):
    return " → ".join(map(str, camino))


def _reconstruir_camino(padre, origen, destino):
    if destino != origen and destino not in padre:
        return []
    camino = [destino]
    while camino[-1] != origen:
        camino.append(padre[camino[-1]])
    return camino[::-1]


def _aristas_de_camino(camino):
    return list(zip(camino, camino[1:]))


def _componer(titulo, pasos, resumen):
    lineas = [titulo]
    lineas.extend(paso.texto for paso in pasos)
    if resumen:
        lineas.append("")
        lineas.extend(resumen)
    return "\n".join(lineas)


def _no_alcanzados(graph, alcanzados):
    return [node for node in sorted(graph.nodes()) if node not in alcanzados]


class AlgorithmsService:
    # ── Recorridos ─────────────────────────────────────────────

    @staticmethod
    def bfs(graph, inicio) -> dict:
        _validar_nodo(graph, inicio)

        pasos = []
        aristas = []
        orden = []
        nivel = {inicio: 0}
        cola = deque([inicio])

        while cola:
            node = cola.popleft()
            orden.append(node)
            pasos.append(Paso(
                "visitar",
                f"Visita nodo {node} (nivel {nivel[node]}) | cola: [{', '.join(map(str, cola))}]",
                nodo=node,
            ))

            for vecino in _vecinos(graph, node):
                if vecino not in nivel:
                    nivel[vecino] = nivel[node] + 1
                    cola.append(vecino)
                    aristas.append((node, vecino))
                    pasos.append(Paso(
                        "descubrir",
                        f"  Va de nodo {node} -> nodo {vecino} (nivel {nivel[vecino]})",
                        nodo=vecino,
                        arista=(node, vecino),
                    ))

        resumen = [
            f"Orden de visita: {', '.join(map(str, orden))}",
            "Niveles: " + ", ".join(f"{node}={nivel[node]}" for node in orden),
        ]
        faltantes = _no_alcanzados(graph, nivel)
        if faltantes:
            resumen.append(f"No alcanzados desde {inicio}: {', '.join(map(str, faltantes))}")

        return {
            "aristas": aristas,
            "pasos": pasos,
            "orden": orden,
            "niveles": nivel,
            "content": _componer("Pasos BFS:", pasos, resumen),
        }

    @staticmethod
    def dfs(graph, inicio) -> dict:
        """DFS iterativo con tiempos de descubrimiento/finalización y
        clasificación de aristas (árbol, retroceso, avance, cruce)."""
        _validar_nodo(graph, inicio)

        dirigido = graph.is_directed()
        pasos = []
        aristas = []
        orden = []
        descubrimiento = {}
        finalizacion = {}
        padre = {inicio: None}
        clasificacion = {"arbol": [], "retroceso": [], "avance": [], "cruce": []}
        tiempo = 0

        def descubrir(node):
            nonlocal tiempo
            tiempo += 1
            descubrimiento[node] = tiempo
            orden.append(node)

        descubrir(inicio)
        pasos.append(Paso("visitar", f"Inicia en nodo {inicio} (t={tiempo})", nodo=inicio))
        pila = [(inicio, iter(_vecinos(graph, inicio)))]

        while pila:
            node, pendientes = pila[-1]
            avanzo = False

            for vecino in pendientes:
                if vecino not in descubrimiento:
                    padre[vecino] = node
                    descubrir(vecino)
                    aristas.append((node, vecino))
                    clasificacion["arbol"].append((node, vecino))
                    pasos.append(Paso(
                        "descubrir",
                        f"Va de nodo {node} -> nodo {vecino} (t={tiempo})",
                        nodo=vecino,
                        arista=(node, vecino),
                    ))
                    pila.append((vecino, iter(_vecinos(graph, vecino))))
                    avanzo = True
                    break

                tipo = AlgorithmsService._clasificar_arista(
                    dirigido, node, vecino, padre, descubrimiento, finalizacion
                )
                if tipo is not None:
                    clasificacion[tipo].append((node, vecino))
                    pasos.append(Paso(
                        "clasificar",
                        f"  Arista {node} -> {vecino}: {tipo}",
                        arista=(node, vecino),
                    ))

            if not avanzo:
                pila.pop()
                tiempo += 1
                finalizacion[node] = tiempo
                pasos.append(Paso("finalizar", f"Finaliza nodo {node} (t={tiempo})", nodo=node))

        resumen = [
            f"Orden de descubrimiento: {', '.join(map(str, orden))}",
            "Tiempos (descubrimiento/finalización): "
            + ", ".join(f"{node}={descubrimiento[node]}/{finalizacion[node]}" for node in orden),
        ]
        for tipo, etiqueta in (("retroceso", "de retroceso"), ("avance", "de avance"), ("cruce", "de cruce")):
            if clasificacion[tipo]:
                resumen.append(
                    f"Aristas {etiqueta}: " + ", ".join(f"{u}->{v}" for u, v in clasificacion[tipo])
                )
        if clasificacion["retroceso"]:
            resumen.append("Hay aristas de retroceso: el recorrido encontró al menos un ciclo.")
        faltantes = _no_alcanzados(graph, descubrimiento)
        if faltantes:
            resumen.append(f"No alcanzados desde {inicio}: {', '.join(map(str, faltantes))}")

        return {
            "aristas": aristas,
            "pasos": pasos,
            "orden": orden,
            "descubrimiento": descubrimiento,
            "finalizacion": finalizacion,
            "clasificacion": clasificacion,
            "content": _componer("Pasos DFS:", pasos, resumen),
        }

    @staticmethod
    def _clasificar_arista(dirigido, node, vecino, padre, descubrimiento, finalizacion):
        en_proceso = vecino not in finalizacion
        if not dirigido:
            # En no dirigidos cada arista se ve dos veces; solo cuenta la que
            # sube hacia un ancestro que no es el padre inmediato.
            if en_proceso and vecino != padre[node]:
                return "retroceso"
            return None
        if en_proceso:
            return "retroceso"
        if descubrimiento[node] < descubrimiento[vecino]:
            return "avance"
        return "cruce"

    # ── Caminos mínimos ────────────────────────────────────────

    @staticmethod
    def dijkstra(graph, inicio, destino=None) -> dict:
        _validar_nodo(graph, inicio)
        if destino is not None:
            _validar_nodo(graph, destino, rol="destino")

        for u, v, data in graph.edges(data=True):
            if data.get("weight", 1) < 0:
                raise ValueError(
                    f"Dijkstra no admite pesos negativos (arista {u} - {v} con peso {data['weight']}). "
                    "Usa Bellman-Ford."
                )

        pasos = []
        distancias = {node: INFINITO for node in graph.nodes()}
        distancias[inicio] = 0
        padre = {}
        visitado = set()
        cola = [(0, inicio)]

        while cola:
            dist_actual, u = heapq.heappop(cola)
            if u in visitado:
                continue

            visitado.add(u)
            pasos.append(Paso("visitar", f"Visitando nodo {u} con distancia mínima {dist_actual:g}", nodo=u))

            for v in _vecinos(graph, u):
                dist_nueva = dist_actual + _peso(graph, u, v)
                if dist_nueva < distancias[v]:
                    distancias[v] = dist_nueva
                    padre[v] = u
                    heapq.heappush(cola, (dist_nueva, v))
                    pasos.append(Paso(
                        "actualizar",
                        f"  -> Actualizando distancia a {v}: {dist_nueva:g} (vía {u})",
                        nodo=v,
                        arista=(u, v),
                    ))

        return AlgorithmsService._resultado_caminos(
            "Pasos Dijkstra:", graph, inicio, destino, distancias, padre, pasos
        )

    @staticmethod
    def bellman_ford(graph, inicio) -> dict:
        """Caminos mínimos con pesos negativos; detecta ciclos negativos."""
        _validar_nodo(graph, inicio)

        aristas_dirigidas = []
        for u, v, data in graph.edges(data=True):
            peso = data.get("weight", 1)
            aristas_dirigidas.append((u, v, peso))
            if not graph.is_directed():
                aristas_dirigidas.append((v, u, peso))
        aristas_dirigidas.sort(key=lambda arista: (arista[0], arista[1]))

        pasos = []
        distancias = {node: INFINITO for node in graph.nodes()}
        distancias[inicio] = 0
        padre = {}

        for iteracion in range(1, graph.number_of_nodes()):
            pasos.append(Paso("iteracion", f"Iteración {iteracion}:"))
            hubo_cambios = False
            for u, v, peso in aristas_dirigidas:
                if distancias[u] != INFINITO and distancias[u] + peso < distancias[v]:
                    distancias[v] = distancias[u] + peso
                    padre[v] = u
                    hubo_cambios = True
                    pasos.append(Paso(
                        "actualizar",
                        f"  -> Relaja {u} -> {v}: distancia a {v} = {distancias[v]:g}",
                        nodo=v,
                        arista=(u, v),
                    ))
            if not hubo_cambios:
                pasos.append(Paso("iteracion", "  Sin cambios: las distancias ya son definitivas."))
                break

        for u, v, peso in aristas_dirigidas:
            if distancias[u] != INFINITO and distancias[u] + peso < distancias[v]:
                ciclo = AlgorithmsService._ciclo_negativo(padre, v, graph.number_of_nodes())
                resumen = [
                    "Se detectó un ciclo de peso negativo alcanzable desde el origen:",
                    _fmt_camino(ciclo),
                    "Las distancias mínimas no están definidas.",
                ]
                if not graph.is_directed():
                    resumen.append("En un grafo no dirigido, toda arista negativa forma un ciclo negativo.")
                return {
                    "aristas": _aristas_de_camino(ciclo),
                    "pasos": pasos,
                    "ciclo_negativo": ciclo,
                    "content": _componer("Pasos Bellman-Ford:", pasos, resumen),
                }

        return AlgorithmsService._resultado_caminos(
            "Pasos Bellman-Ford:", graph, inicio, None, distancias, padre, pasos
        )

    @staticmethod
    def _ciclo_negativo(padre, node, total_nodos):
        # Retroceder n pasos garantiza caer dentro del ciclo.
        for _ in range(total_nodos):
            node = padre[node]
        ciclo = [node]
        actual = padre[node]
        while actual != node:
            ciclo.append(actual)
            actual = padre[actual]
        ciclo.append(node)
        return ciclo[::-1]

    @staticmethod
    def _resultado_caminos(titulo, graph, inicio, destino, distancias, padre, pasos):
        caminos = {
            node: _reconstruir_camino(padre, inicio, node)
            for node in graph.nodes()
            if distancias[node] != INFINITO
        }

        resumen = ["Distancias finales desde el origen:"]
        for node in sorted(graph.nodes()):
            linea = f"Nodo {node}: {_fmt_dist(distancias[node])}"
            if node in caminos and node != inicio:
                linea += f"  (camino: {_fmt_camino(caminos[node])})"
            resumen.append(linea)

        if destino is None:
            aristas = [(origen, node) for node, origen in padre.items()]
        else:
            camino = caminos.get(destino, [])
            aristas = _aristas_de_camino(camino)
            resumen.append("")
            if camino:
                resumen.append(
                    f"Camino más corto de {inicio} a {destino}: {_fmt_camino(camino)} "
                    f"(costo {_fmt_dist(distancias[destino])})"
                )
            else:
                resumen.append(f"No existe camino de {inicio} a {destino}.")

        return {
            "aristas": aristas,
            "pasos": pasos,
            "distancias": distancias,
            "caminos": caminos,
            "content": _componer(titulo, pasos, resumen),
        }

    # ── Árbol de expansión mínima ──────────────────────────────

    @staticmethod
    def _validar_no_dirigido(graph, nombre):
        if graph.is_directed():
            raise ValueError(f"{nombre} solo se puede ejecutar en grafos no dirigidos.")
        if graph.number_of_edges() == 0:
            raise ValueError("El grafo no tiene aristas para construir el árbol.")

    @staticmethod
    def _resumen_mst(graph, aristas, peso_total, nombre_arbol="MST"):
        resumen = [f"Peso total del {nombre_arbol}: {peso_total:g}"]
        arboles = graph.number_of_nodes() - len(aristas)
        if arboles > 1:
            resumen.append(
                f"El grafo no es conexo: el resultado es un bosque de {arboles} árboles "
                "(uno por componente)."
            )
        return resumen

    @staticmethod
    def kruskal(graph) -> dict:
        AlgorithmsService._validar_no_dirigido(graph, "Kruskal")

        aristas_ordenadas = sorted(
            (data.get("weight", 1), min(u, v), max(u, v))
            for u, v, data in graph.edges(data=True)
        )
        parent = {node: node for node in graph.nodes()}
        rank = {node: 0 for node in graph.nodes()}

        def find(node):
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        def union(a, b):
            raiz_a, raiz_b = find(a), find(b)
            if raiz_a == raiz_b:
                return False
            if rank[raiz_a] < rank[raiz_b]:
                raiz_a, raiz_b = raiz_b, raiz_a
            parent[raiz_b] = raiz_a
            if rank[raiz_a] == rank[raiz_b]:
                rank[raiz_a] += 1
            return True

        pasos = []
        aristas_mst = []
        descartadas = []
        peso_total = 0
        for peso, u, v in aristas_ordenadas:
            if union(u, v):
                aristas_mst.append((u, v))
                peso_total += peso
                pasos.append(Paso("agregar", f"Arista añadida: {u} - {v} (Peso: {peso:g})", arista=(u, v)))
            else:
                descartadas.append((u, v))
                pasos.append(Paso("descartar", f"  Descartada: {u} - {v} (Peso: {peso:g}) formaría un ciclo", arista=(u, v)))

        return {
            "aristas": aristas_mst,
            "pasos": pasos,
            "descartadas": descartadas,
            "peso_total": peso_total,
            "content": _componer("Pasos Kruskal:", pasos, AlgorithmsService._resumen_mst(graph, aristas_mst, peso_total)),
        }

    @staticmethod
    def prim(graph, inicio=None) -> dict:
        AlgorithmsService._validar_no_dirigido(graph, "Prim")
        if inicio is not None:
            _validar_nodo(graph, inicio)

        pendientes = sorted(graph.nodes())
        if inicio is not None:
            pendientes.remove(inicio)
            pendientes.insert(0, inicio)

        pasos = []
        aristas_mst = []
        visitados = set()
        peso_total = 0

        for raiz in pendientes:
            if raiz in visitados:
                continue
            if visitados:
                pasos.append(Paso("visitar", f"Nueva componente: se reinicia desde el nodo {raiz}", nodo=raiz))
            else:
                pasos.append(Paso("visitar", f"Inicia en nodo {raiz}", nodo=raiz))
            visitados.add(raiz)
            frontera = [(_peso(graph, raiz, v), raiz, v) for v in _vecinos(graph, raiz)]
            heapq.heapify(frontera)

            while frontera:
                peso, u, v = heapq.heappop(frontera)
                if v in visitados:
                    continue
                visitados.add(v)
                aristas_mst.append((u, v))
                peso_total += peso
                pasos.append(Paso(
                    "agregar",
                    f"Arista añadida: {u} - {v} (Peso: {peso:g}), la más barata hacia fuera del árbol",
                    nodo=v,
                    arista=(u, v),
                ))
                for w in _vecinos(graph, v):
                    if w not in visitados:
                        heapq.heappush(frontera, (_peso(graph, v, w), v, w))

        return {
            "aristas": aristas_mst,
            "pasos": pasos,
            "peso_total": peso_total,
            "content": _componer("Pasos Prim:", pasos, AlgorithmsService._resumen_mst(graph, aristas_mst, peso_total)),
        }

    # ── Análisis estructural ───────────────────────────────────

    @staticmethod
    def orden_topologico(graph) -> dict:
        """Algoritmo de Kahn: requiere un grafo dirigido acíclico."""
        if not graph.is_directed():
            raise ValueError("El orden topológico solo existe en grafos dirigidos.")

        grado_entrada = {node: graph.in_degree(node) for node in graph.nodes()}
        disponibles = [node for node in sorted(graph.nodes()) if grado_entrada[node] == 0]
        heapq.heapify(disponibles)

        pasos = []
        orden = []
        while disponibles:
            node = heapq.heappop(disponibles)
            orden.append(node)
            pasos.append(Paso("visitar", f"Toma nodo {node} (sin dependencias pendientes)", nodo=node))
            for sucesor in _vecinos(graph, node):
                grado_entrada[sucesor] -= 1
                if grado_entrada[sucesor] == 0:
                    heapq.heappush(disponibles, sucesor)
                    pasos.append(Paso("descubrir", f"  {sucesor} queda libre", nodo=sucesor, arista=(node, sucesor)))

        if len(orden) < graph.number_of_nodes():
            bloqueados = [node for node in sorted(graph.nodes()) if node not in orden]
            resumen = [
                "El grafo tiene al menos un ciclo: no admite orden topológico.",
                f"Nodos atrapados en ciclos o detrás de ellos: {', '.join(map(str, bloqueados))}",
            ]
            return {
                "aristas": [],
                "pasos": pasos,
                "orden": None,
                "content": _componer("Pasos Orden Topológico:", pasos, resumen),
            }

        return {
            "aristas": [],
            "pasos": pasos,
            "orden": orden,
            "content": _componer(
                "Pasos Orden Topológico:", pasos, [f"Orden topológico: {', '.join(map(str, orden))}"]
            ),
        }

    @staticmethod
    def detectar_ciclo(graph) -> dict:
        try:
            ciclo = [(u, v) for u, v, *_ in nx.find_cycle(graph)]
        except nx.NetworkXNoCycle:
            tipo = "DAG (dirigido acíclico)" if graph.is_directed() else "bosque (sin ciclos)"
            return {
                "aristas": [],
                "pasos": [],
                "ciclo": None,
                "content": f"Detección de ciclos:\nNo se encontraron ciclos. El grafo es un {tipo}.",
            }

        nodos = [u for u, _ in ciclo] + [ciclo[-1][1]]
        return {
            "aristas": ciclo,
            "pasos": [Paso("ciclo", f"{u} -> {v}", arista=(u, v)) for u, v in ciclo],
            "ciclo": nodos,
            "content": f"Detección de ciclos:\nCiclo encontrado: {_fmt_camino(nodos)}",
        }

    @staticmethod
    def componentes_fuertes(graph) -> dict:
        if not graph.is_directed():
            raise ValueError("Las componentes fuertemente conexas se calculan en grafos dirigidos.")

        componentes = sorted(
            (sorted(componente) for componente in nx.strongly_connected_components(graph)),
            key=lambda componente: (-len(componente), componente[0]),
        )
        indice = {node: i for i, componente in enumerate(componentes) for node in componente}
        aristas = [(u, v) for u, v in graph.edges() if indice[u] == indice[v]]

        lineas = [f"Componentes fuertemente conexas: {len(componentes)}"]
        for i, componente in enumerate(componentes, start=1):
            lineas.append(f"{i}. {{{', '.join(map(str, componente))}}}")

        return {
            "aristas": aristas,
            "pasos": [],
            "componentes": componentes,
            "content": "\n".join(lineas),
        }
