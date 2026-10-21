"""Estado visual de un algoritmo después de aplicar sus primeros k pasos.

Es la base de la ejecución paso a paso: dado el registro de pasos de un
algoritmo (core.algorithms.Paso), calcula qué nodos y aristas destacar.
"""
from dataclasses import dataclass, field
from typing import Any

# Estados de nodo (un nodo sin estado está pendiente).
FRONTERA = 'frontera'      # descubierto / en espera (en cola, distancia tentativa)
ACTUAL = 'actual'          # el que se está procesando
VISITADO = 'visitado'      # ya procesado (en DFS: en proceso)
FINALIZADO = 'finalizado'  # DFS: todos sus descendientes terminaron

# Estados de arista.
ARBOL = 'arbol'            # forma parte del árbol / camino en construcción
CANDIDATA = 'candidata'    # mejor opción conocida hasta ahora (relajación)
DESCARTADA = 'descartada'  # evaluada y rechazada (p. ej. formaría un ciclo)
NO_ARBOL = 'no_arbol'      # DFS: retroceso, avance o cruce
RESULTADO = 'resultado'    # parte del resultado final


def clave_arista(u, v, dirigido):
    """En no dirigidos (u, v) y (v, u) son la misma arista."""
    return (u, v) if dirigido else tuple(sorted((u, v)))


@dataclass
class EstadoVisual:
    dirigido: bool
    nodos: dict[Any, str] = field(default_factory=dict)
    aristas: dict[tuple, str] = field(default_factory=dict)
    paso: Any = None
    final: bool = False
    # Si el algoritmo marca nodos en algún paso; si no (p. ej. detección de
    # ciclos), los nodos conservan sus colores normales.
    usa_estados_de_nodo: bool = False

    def estado_arista(self, u, v):
        return self.aristas.get(clave_arista(u, v, self.dirigido))


def estado_hasta(pasos, k, aristas_finales=(), dirigido=False):
    """Aplica los primeros k pasos. Con k >= len(pasos) devuelve el resultado final."""
    k = max(0, min(k, len(pasos)))
    nodos = {}
    aristas = {}
    candidata_hacia = {}
    actual = None

    def mover_a(nodo):
        nonlocal actual
        if actual is not None and nodos.get(actual) == ACTUAL:
            nodos[actual] = VISITADO
        actual = nodo
        nodos[nodo] = ACTUAL

    def marcar(nodo, estado, sin_retroceder=(ACTUAL, VISITADO, FINALIZADO)):
        if nodos.get(nodo) not in sin_retroceder:
            nodos[nodo] = estado

    for paso in pasos[:k]:
        clave = clave_arista(*paso.arista, dirigido) if paso.arista else None

        if paso.tipo == 'visitar':
            mover_a(paso.nodo)
        elif paso.tipo == 'avanzar':
            aristas[clave] = ARBOL
            mover_a(paso.nodo)
        elif paso.tipo == 'descubrir':
            aristas[clave] = ARBOL
            marcar(paso.nodo, FRONTERA)
        elif paso.tipo == 'clasificar':
            aristas[clave] = NO_ARBOL
            if nodos.get(paso.arista[0]) != FINALIZADO:
                mover_a(paso.arista[0])
        elif paso.tipo == 'finalizar':
            nodos[paso.nodo] = FINALIZADO
            if actual == paso.nodo:
                actual = None
        elif paso.tipo == 'actualizar':
            # Solo la mejor arista conocida hacia cada nodo queda como candidata.
            anterior = candidata_hacia.get(paso.nodo)
            if anterior is not None and aristas.get(anterior) == CANDIDATA:
                del aristas[anterior]
            aristas[clave] = CANDIDATA
            candidata_hacia[paso.nodo] = clave
            marcar(paso.nodo, FRONTERA)
        elif paso.tipo == 'agregar':
            aristas[clave] = ARBOL
            for extremo in paso.arista:
                marcar(extremo, VISITADO, sin_retroceder=(ACTUAL, FINALIZADO))
            if paso.nodo is not None:
                mover_a(paso.nodo)
        elif paso.tipo == 'descartar':
            aristas[clave] = DESCARTADA
        elif paso.tipo == 'ciclo':
            aristas[clave] = RESULTADO
        # 'iteracion' solo aporta texto.

    final = k == len(pasos)
    if final:
        nodos = {nodo: (VISITADO if estado in (ACTUAL, FRONTERA) else estado) for nodo, estado in nodos.items()}
        aristas = {clave: estado for clave, estado in aristas.items() if estado in (DESCARTADA, NO_ARBOL)}
        for u, v in aristas_finales:
            aristas[clave_arista(u, v, dirigido)] = RESULTADO

    return EstadoVisual(
        dirigido=dirigido,
        nodos=nodos,
        aristas=aristas,
        paso=pasos[k - 1] if k > 0 else None,
        final=final,
        usa_estados_de_nodo=any(paso.nodo is not None or paso.tipo == 'agregar' for paso in pasos),
    )
