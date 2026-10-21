import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from core.graph_model import GraphModel
from core.graph_service import GraphService
from core.history import History
from ui import theme

MODO_SELECCIONAR = 'seleccionar'
MODO_NODO = 'nodo'
MODO_ARISTA = 'arista'

TAMANO_NODO = 700
TAMANO_NODO_DESTACADO = 950
# Curvatura de las aristas dirigidas que tienen una opuesta (u -> v y v -> u).
RADIO_CURVA = 0.18
# Tiempo mínimo entre redibujados durante un arrastre (~60 fps).
INTERVALO_REDIBUJO_MS = 16
# Tolerancias de clic en píxeles: no dependen del nivel de zoom.
TOLERANCIA_NODO_PX = 4
TOLERANCIA_ARISTA_PX = 6
UMBRAL_ARRASTRE_PX = 3


@dataclass(frozen=True)
class ObjetivoClic:
    """Lo que hay bajo el cursor: un nodo, una arista o el fondo."""
    tipo: str
    valor: Any = None
    x: float = 0.0
    y: float = 0.0


class Lienzo(QObject):
    """Dibuja el grafo y traduce la interacción del mouse en ediciones del modelo.

    No abre diálogos de la aplicación: pide lo que necesita mediante señales
    y la ventana principal decide cómo responder.
    """

    grafoCambiado = pyqtSignal()
    seleccionCambiada = pyqtSignal()
    resultadoDescartado = pyqtSignal()
    tipoGrafoCambiado = pyqtSignal(str)
    mensaje = pyqtSignal(str)
    menuContextualSolicitado = pyqtSignal(object)
    aristaSolicitada = pyqtSignal(object, object)
    edicionPesoSolicitada = pyqtSignal(object, object)
    cursorMovido = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = GraphModel()
        self.modo = MODO_SELECCIONAR
        self.origen_arista = None
        self.dragging_node = None
        self.selected_node = None
        self.selected_edge = None
        self.selected_nodes = set()
        self.selected_edges = set()
        self.analysis_highlighted_nodes = {}
        self.component_nodes = set()
        self.is_panning = False
        self.pan_origin = None
        self.pan_start_px = None
        self._pan_movido = False
        self.visual_filter = 'all'
        self.history = History()
        # Estado previo al arrastre; se registra solo si el nodo realmente se mueve.
        self._drag_snapshot = None
        # Durante un arrastre llegan muchos eventos; se agrupan en un redibujo.
        self._timer_redibujo = QTimer(self)
        self._timer_redibujo.setSingleShot(True)
        self._timer_redibujo.setInterval(INTERVALO_REDIBUJO_MS)
        self._timer_redibujo.timeout.connect(self.DibujarGrafo)

        # Documento: archivo asociado y estado guardado (para detectar cambios).
        self.ruta_actual = None
        self._nombre_sin_ruta = "Sin título"
        self._snapshot_guardado = self.model.to_dict()

        # Figure (no pyplot): evita el estado global de pyplot dentro de Qt.
        self.fig = Figure(figsize=(8.5, 5.8))
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.ax = self.fig.add_subplot()
        self.fig.patch.set_facecolor(theme.FONDO)
        self.ax.set_facecolor(theme.FONDO)
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.ax.set_position([0, 0, 1, 1])
        self.canvas.mpl_connect('button_press_event', self.MouseClick)
        self.canvas.mpl_connect('motion_notify_event', self.MouseMove)
        self.canvas.mpl_connect('button_release_event', self.MouseRelease)
        self.canvas.mpl_connect('scroll_event', self.MouseWheel)
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.axis('off')

    # Accesos directos al modelo (el modelo es la única fuente de verdad).
    @property
    def graph(self):
        return self.model.graph

    @property
    def pos(self):
        return self.model.pos

    @property
    def edge_colors(self):
        return self.model.edge_colors

    # Los límites se leen siempre de los ejes para que el zoom propio y
    # cualquier cambio externo de la vista no se pisen entre sí.
    @property
    def current_xlim(self):
        return list(self.ax.get_xlim())

    @current_xlim.setter
    def current_xlim(self, limits):
        self.ax.set_xlim(*limits)

    @property
    def current_ylim(self):
        return list(self.ax.get_ylim())

    @current_ylim.setter
    def current_ylim(self, limits):
        self.ax.set_ylim(*limits)

    # ── Modos de edición ───────────────────────────────────────

    def setModo(self, modo):
        self.modo = modo
        self.cancelarAccion(limpiar_seleccion=False)

    def cancelarAccion(self, limpiar_seleccion=True):
        """Esc: cancela una arista a medio crear y, si no había, limpia la selección."""
        if self.origen_arista is not None:
            self.origen_arista = None
            self.mensaje.emit("Creación de arista cancelada.")
        elif limpiar_seleccion:
            self.clearSelection()
            self.seleccionCambiada.emit()
        self.DibujarGrafo()

    def cambiarTipoGrafo(self, tipo, conservar=True):
        """Cambia el tipo de grafo convirtiendo las aristas o empezando vacío (se puede deshacer)."""
        self._checkpoint()
        if not conservar:
            self.model.clear()
            self.component_nodes = set()
        self.model.set_graph_type(tipo)
        self.clearSelection()
        self._refresh_after_change()

    # ── Historial ──────────────────────────────────────────────

    def _checkpoint(self, invalida_resultado=True):
        """Registra el estado actual antes de modificar el grafo.

        Si la modificación cambia la estructura, el resultado del último
        algoritmo deja de corresponder al grafo y se descarta.
        """
        self.history.push(self.model.to_dict())
        if invalida_resultado:
            self._descartarResultado()

    def _descartarResultado(self):
        self.model.edge_colors.clear()
        self.clearAnalysisHighlights()
        self.resultadoDescartado.emit()

    def Deshacer(self):
        if self._restaurar(self.history.undo(self.model.to_dict())):
            self.mensaje.emit("Cambio deshecho.")

    def Rehacer(self):
        if self._restaurar(self.history.redo(self.model.to_dict())):
            self.mensaje.emit("Cambio rehecho.")

    def _restaurar(self, snapshot):
        if snapshot is None:
            return False
        self.model.load_from_dict(snapshot)
        self.origen_arista = None
        self._descartarResultado()
        self.tipoGrafoCambiado.emit(self.model.graph_type)
        self._refresh_after_change()
        return True

    # ── Selección ──────────────────────────────────────────────

    def clearSelection(self):
        self.selected_node = None
        self.selected_edge = None
        self.selected_nodes.clear()
        self.selected_edges.clear()
        self.dragging_node = None

    def _prune_selection(self):
        """Descarta de la selección los nodos/aristas que ya no existen en el grafo."""
        graph = self.model.graph
        if self.selected_node is not None and self.selected_node not in graph:
            self.selected_node = None
        if self.selected_edge is not None and not graph.has_edge(*self.selected_edge):
            self.selected_edge = None
        if self.dragging_node is not None and self.dragging_node not in graph:
            self.dragging_node = None
        if self.origen_arista is not None and self.origen_arista not in graph:
            self.origen_arista = None
        self.selected_nodes = {node for node in self.selected_nodes if node in graph}
        self.selected_edges = {edge for edge in self.selected_edges if graph.has_edge(*edge)}

    def _refresh_after_change(self):
        """Limpia selección inválida y refresca el lienzo y los paneles."""
        self._prune_selection()
        self.DibujarGrafo()
        self.grafoCambiado.emit()
        self.seleccionCambiada.emit()

    def _seleccionar(self, nodo=None, arista=None, acumular=False):
        if acumular:
            if nodo is not None:
                self.selected_nodes ^= {nodo}
                self.selected_node = nodo if nodo in self.selected_nodes else None
                self.selected_edge = None
            if arista is not None:
                self.selected_edges ^= {arista}
                self.selected_edge = arista if arista in self.selected_edges else None
                self.selected_node = None
        else:
            self.clearSelection()
            self.selected_node = nodo
            self.selected_edge = arista
        self.DibujarGrafo()
        self.seleccionCambiada.emit()

    # ── Edición ────────────────────────────────────────────────

    def agregarNodo(self, x, y):
        node_id = 1 if self.graph.number_of_nodes() == 0 else max(self.graph.nodes()) + 1
        self._checkpoint()
        self.model.add_node(node_id, (x, y))
        self.clearSelection()
        self._refresh_after_change()
        self.mensaje.emit(f"Nodo {node_id} creado.")
        return node_id

    def DibujarArista(self, posNodo1, posNodo2, peso=1):
        for nodo in (posNodo1, posNodo2):
            if nodo not in self.graph:
                self.Alertas(f"El nodo {nodo} no se encuentra.")
                return

        if posNodo1 == posNodo2:
            self.Alertas("Una arista debe unir dos nodos distintos.", titulo="Arista no válida")
            return

        if self.graph.has_edge(posNodo1, posNodo2):
            peso_actual = self.graph.edges[posNodo1, posNodo2].get('weight', 1)
            if peso_actual == peso:
                return
            if not self.alertaConfirmacion(
                f"La arista {posNodo1} - {posNodo2} ya existe con peso {peso_actual}.\n"
                f"¿Reemplazar su peso por {peso}?"
            ):
                return

        self._checkpoint()
        self.model.add_edge(posNodo1, posNodo2, peso=peso)
        self._refresh_after_change()
        self.mensaje.emit(f"Arista {posNodo1} - {posNodo2} (peso {peso}) creada.")

    def Alertas(self, mensaje, titulo="Elemento no encontrado"):
        alerta = QMessageBox(self.canvas)
        alerta.setIcon(QMessageBox.Icon.Warning)
        alerta.setText(titulo)
        alerta.setInformativeText(mensaje)
        alerta.setWindowTitle("Alerta")
        alerta.exec()

    def alertaConfirmacion(self, mensaje):
        alerta = QMessageBox(self.canvas)
        alerta.setIcon(QMessageBox.Icon.Warning)
        alerta.setText(mensaje)
        alerta.setWindowTitle('Confirmación requerida')
        btnSi = alerta.addButton('Sí', QMessageBox.ButtonRole.YesRole)
        alerta.addButton('Cancelar', QMessageBox.ButtonRole.NoRole)
        alerta.exec()
        return alerta.clickedButton() == btnSi

    # ── Mouse ──────────────────────────────────────────────────

    def objetivoEn(self, x, y):
        nodo = self._find_node_at_position(x, y)
        if nodo is not None:
            return ObjetivoClic('nodo', nodo, x, y)
        arista = self._find_edge_at_position(x, y)
        if arista is not None:
            return ObjetivoClic('arista', arista, x, y)
        return ObjetivoClic('fondo', None, x, y)

    def MouseClick(self, event):
        if event.xdata is None or event.ydata is None:
            return

        objetivo = self.objetivoEn(event.xdata, event.ydata)
        acumular = event.key in ('control', 'shift')

        if event.button == 3:
            self._clicDerecho(objetivo)
            return

        if event.button == 2:
            self._iniciarPan(event)
            return

        if event.button != 1:
            return

        if getattr(event, 'dblclick', False):
            if objetivo.tipo == 'arista':
                self.edicionPesoSolicitada.emit(*objetivo.valor)
            return

        if self.modo == MODO_NODO and objetivo.tipo == 'fondo':
            self.agregarNodo(event.xdata, event.ydata)
            return

        if self.modo == MODO_ARISTA:
            self._clicModoArista(objetivo)
            return

        if objetivo.tipo == 'nodo':
            self._seleccionar(nodo=objetivo.valor, acumular=acumular)
            if not acumular:
                self.dragging_node = objetivo.valor
                self._drag_snapshot = self.model.to_dict()
        elif objetivo.tipo == 'arista':
            self._seleccionar(arista=objetivo.valor, acumular=acumular)
        else:
            # Arrastrar el fondo desplaza la vista; un clic sin mover deselecciona.
            self._iniciarPan(event)

    def _clicDerecho(self, objetivo):
        if objetivo.tipo == 'nodo' and objetivo.valor not in self.selected_nodes:
            self._seleccionar(nodo=objetivo.valor)
        elif objetivo.tipo == 'arista' and objetivo.valor not in self.selected_edges:
            self._seleccionar(arista=objetivo.valor)
        self.menuContextualSolicitado.emit(objetivo)

    def _clicModoArista(self, objetivo):
        if objetivo.tipo != 'nodo':
            if self.origen_arista is not None:
                self.cancelarAccion(limpiar_seleccion=False)
            return

        nodo = objetivo.valor
        if self.origen_arista is None:
            self.origen_arista = nodo
            self.DibujarGrafo()
            self.mensaje.emit(f"Origen: nodo {nodo}. Haz clic en el nodo destino (Esc para cancelar).")
            return

        if nodo == self.origen_arista:
            self.cancelarAccion(limpiar_seleccion=False)
            return

        origen = self.origen_arista
        self.origen_arista = None
        self.DibujarGrafo()
        self.aristaSolicitada.emit(origen, nodo)

    def _iniciarPan(self, event):
        self.is_panning = True
        self._pan_movido = False
        self.pan_origin = self.current_xlim + self.current_ylim
        # Se guardan píxeles: las coordenadas de datos cambian mientras la vista se mueve.
        self.pan_start_px = (event.x, event.y)

    def _a_pixeles(self, x, y):
        return self.ax.transData.transform((x, y))

    def _radio_nodo_px(self):
        radio_puntos = math.sqrt(TAMANO_NODO / math.pi)
        return radio_puntos * self.fig.dpi / 72

    def _nodos_visibles(self):
        return set(self._get_visible_graph().nodes())

    def _find_node_at_position(self, x, y):
        """Nodo visible más cercano al punto, si el punto cae dentro de su círculo."""
        px, py = self._a_pixeles(x, y)
        limite = self._radio_nodo_px() + TOLERANCIA_NODO_PX
        mejor, mejor_distancia = None, limite
        for node_id in self._nodos_visibles():
            nx_px, ny_px = self._a_pixeles(*self.pos[node_id])
            distancia = math.hypot(px - nx_px, py - ny_px)
            if distancia <= mejor_distancia:
                mejor, mejor_distancia = node_id, distancia
        return mejor

    def _find_edge_at_position(self, x, y):
        """Arista visible más cercana al punto (en píxeles)."""
        punto = self._a_pixeles(x, y)
        mejor, mejor_distancia = None, TOLERANCIA_ARISTA_PX
        for u, v in self._get_visible_graph().edges():
            trazo = self._trazo_arista_px(u, v)
            distancia = min(
                self._distance_to_segment(punto, inicio, fin) for inicio, fin in zip(trazo, trazo[1:])
            )
            if distancia <= mejor_distancia:
                mejor, mejor_distancia = (u, v), distancia
        return mejor

    def _es_curva(self, u, v):
        return self.graph.is_directed() and self.graph.has_edge(v, u)

    def _trazo_arista_px(self, u, v, muestras=16):
        """Puntos (en píxeles) por los que pasa la arista tal como se dibuja."""
        p1 = self._a_pixeles(*self.pos[u])
        p2 = self._a_pixeles(*self.pos[v])
        if not self._es_curva(u, v):
            return [p1, p2]

        # Misma geometría que el 'arc3' de matplotlib: Bézier cuadrática cuyo
        # punto de control se desplaza rad * (dy, -dx) desde el punto medio.
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        control = ((p1[0] + p2[0]) / 2 + RADIO_CURVA * dy, (p1[1] + p2[1]) / 2 - RADIO_CURVA * dx)
        puntos = []
        for i in range(muestras + 1):
            t = i / muestras
            a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t ** 2
            puntos.append((a * p1[0] + b * control[0] + c * p2[0], a * p1[1] + b * control[1] + c * p2[1]))
        return puntos

    def _distance_to_segment(self, point, start, end):
        px, py = point
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)

        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))

        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        return math.hypot(px - closest_x, py - closest_y)

    def MouseMove(self, event):
        if event.xdata is not None and event.ydata is not None:
            self.cursorMovido.emit(event.xdata, event.ydata)

        if self.is_panning and self.pan_origin is not None and self.pan_start_px is not None:
            desplazamiento_x = event.x - self.pan_start_px[0]
            desplazamiento_y = event.y - self.pan_start_px[1]
            if not self._pan_movido and math.hypot(desplazamiento_x, desplazamiento_y) < UMBRAL_ARRASTRE_PX:
                return
            self._pan_movido = True

            x0, x1, y0, y1 = self.pan_origin
            bbox = self.ax.bbox
            dx = desplazamiento_x * (x1 - x0) / bbox.width
            dy = desplazamiento_y * (y1 - y0) / bbox.height

            self.current_xlim = [x0 - dx, x1 - dx]
            self.current_ylim = [y0 - dy, y1 - dy]
            self.canvas.draw_idle()
            return

        if event.xdata is None or event.ydata is None or self.dragging_node is None:
            return

        if self._drag_snapshot is not None:
            # Primer movimiento real del arrastre: mover no invalida resultados.
            self.history.push(self._drag_snapshot)
            self._drag_snapshot = None

        self.model.set_node_position(self.dragging_node, (event.xdata, event.ydata))
        if not self._timer_redibujo.isActive():
            self._timer_redibujo.start()

    def MouseRelease(self, event):
        hubo_arrastre = self.dragging_node is not None and self._drag_snapshot is None
        clic_en_fondo = self.is_panning and not self._pan_movido and event.button == 1

        self._drag_snapshot = None
        self.dragging_node = None
        self.is_panning = False
        self.pan_origin = None
        self.pan_start_px = None

        if hubo_arrastre:
            # La posición del panel y el estado de "cambios sin guardar" cambiaron.
            self._refresh_after_change()
        elif clic_en_fondo and (self.selected_node is not None or self.selected_edge is not None
                                or self.selected_nodes or self.selected_edges):
            self._seleccionar()

    def MouseWheel(self, event):
        if event.xdata is None or event.ydata is None:
            return

        zoom_factor = 1.1 if event.step > 0 else 1 / 1.1
        x0, x1 = self.current_xlim
        y0, y1 = self.current_ylim
        x_range = x1 - x0
        y_range = y1 - y0

        x_ratio = (event.xdata - x0) / x_range
        y_ratio = (event.ydata - y0) / y_range

        new_x_range = max(0.05, x_range / zoom_factor)
        new_y_range = max(0.05, y_range / zoom_factor)

        self.current_xlim = [
            event.xdata - x_ratio * new_x_range,
            event.xdata + (1 - x_ratio) * new_x_range,
        ]
        self.current_ylim = [
            event.ydata - y_ratio * new_y_range,
            event.ydata + (1 - y_ratio) * new_y_range,
        ]
        self.canvas.draw_idle()

    # ── Vista ──────────────────────────────────────────────────

    def resetView(self):
        self.current_xlim = [0, 1]
        self.current_ylim = [0, 1]
        self.canvas.draw_idle()

    def ajustarVista(self):
        """Encuadra todos los nodos visibles con un margen."""
        nodos = self._nodos_visibles()
        if not nodos:
            self.resetView()
            return

        xs = [self.pos[node][0] for node in nodos]
        ys = [self.pos[node][1] for node in nodos]
        ancho = max(max(xs) - min(xs), 0.2)
        alto = max(max(ys) - min(ys), 0.2)
        centro_x = (max(xs) + min(xs)) / 2
        centro_y = (max(ys) + min(ys)) / 2
        margen = 1.3

        self.current_xlim = [centro_x - ancho * margen / 2, centro_x + ancho * margen / 2]
        self.current_ylim = [centro_y - alto * margen / 2, centro_y + alto * margen / 2]
        self.canvas.draw_idle()

    def zoomIn(self):
        self._apply_zoom(1.15)

    def zoomOut(self):
        self._apply_zoom(1 / 1.15)

    def _apply_zoom(self, zoom_factor):
        x0, x1 = self.current_xlim
        y0, y1 = self.current_ylim
        center_x = (x0 + x1) / 2
        center_y = (y0 + y1) / 2

        x_range = max(0.05, (x1 - x0) / zoom_factor)
        y_range = max(0.05, (y1 - y0) / zoom_factor)

        self.current_xlim = [center_x - x_range / 2, center_x + x_range / 2]
        self.current_ylim = [center_y - y_range / 2, center_y + y_range / 2]
        self.canvas.draw_idle()

    def clearAnalysisHighlights(self):
        self.analysis_highlighted_nodes = {}

    def setAnalysisHighlights(self, node_scores):
        self.analysis_highlighted_nodes = dict(node_scores)

    def setVisualFilter(self, mode):
        self.visual_filter = mode if mode in {'all', 'hide_isolated', 'component'} else 'all'
        if mode != 'component':
            self.component_nodes = set()
        self.DibujarGrafo()
        self.grafoCambiado.emit()

    def focusCurrentComponent(self):
        pivot = self.selected_node
        if pivot is None:
            return False

        if self.graph.is_directed():
            components = nx.weakly_connected_components(self.graph)
        else:
            components = nx.connected_components(self.graph)

        for component in components:
            if pivot in component:
                self.component_nodes = set(component)
                self.visual_filter = 'component'
                self.DibujarGrafo()
                self.grafoCambiado.emit()
                return True

        return False

    def _get_visible_graph(self):
        if self.visual_filter == 'hide_isolated':
            visible_nodes = [node for node in self.graph.nodes() if self.graph.degree(node) > 0]
            return self.graph.subgraph(visible_nodes).copy()
        if self.visual_filter == 'component':
            visible_nodes = list(self.component_nodes) if self.component_nodes else list(self.graph.nodes())
            return self.graph.subgraph(visible_nodes).copy()
        return self.graph.copy()

    # ── Dibujo ─────────────────────────────────────────────────

    def DibujarGrafo(self):
        self._timer_redibujo.stop()
        visible_graph = self._get_visible_graph()

        xlim, ylim = self.current_xlim, self.current_ylim
        self.ax.clear()
        self.current_xlim = xlim
        self.current_ylim = ylim
        self.ax.axis('off')

        if visible_graph.number_of_nodes() == 0:
            self.canvas.draw_idle()
            return

        nodos = list(visible_graph.nodes())
        estilos = {node: self._estilo_nodo(visible_graph, node) for node in nodos}
        tamanos = [estilos[node]['tamano'] for node in nodos]

        nx.draw_networkx_nodes(
            visible_graph,
            pos=self.pos,
            nodelist=nodos,
            node_color=[estilos[node]['relleno'] for node in nodos],
            node_size=tamanos,
            edgecolors=[estilos[node]['borde'] for node in nodos],
            linewidths=[estilos[node]['grosor'] for node in nodos],
            ax=self.ax,
        )
        self._dibujarAristas(visible_graph, nodos, tamanos)

        # Las etiquetas se agrupan por color de texto (claro u oscuro según el relleno).
        for color_texto in {estilo['texto'] for estilo in estilos.values()}:
            nx.draw_networkx_labels(
                visible_graph,
                pos=self.pos,
                labels={node: str(node) for node in nodos if estilos[node]['texto'] == color_texto},
                font_size=11,
                font_color=color_texto,
                font_weight='bold',
                ax=self.ax,
            )

        self.canvas.draw_idle()

    def _estilo_nodo(self, graph, node):
        estilo = {
            'relleno': self._color_componente(node),
            'borde': '#ffffff',
            'grosor': 1.5,
            'tamano': TAMANO_NODO,
        }

        if node in self.analysis_highlighted_nodes:
            # Tamaño proporcional al puntaje del análisis (p. ej. centralidad).
            maximo = max(self.analysis_highlighted_nodes.values()) or 1
            proporcion = self.analysis_highlighted_nodes[node] / maximo
            estilo['tamano'] = 450 + 1100 * proporcion
        elif graph.degree(node) == 0:
            estilo['relleno'] = theme.NODO_AISLADO

        if node == self.origen_arista:
            estilo.update(relleno=theme.NODO_ORIGEN_ARISTA, borde=theme.BORDE_ORIGEN_ARISTA, grosor=3,
                          tamano=max(estilo['tamano'], TAMANO_NODO_DESTACADO))
        elif node in self.selected_nodes or node == self.selected_node:
            estilo.update(relleno=theme.NODO_SELECCIONADO, borde=theme.BORDE_SELECCIONADO, grosor=3,
                          tamano=max(estilo['tamano'], TAMANO_NODO_DESTACADO))

        estilo['texto'] = theme.texto_sobre(estilo['relleno'])
        return estilo

    def _color_componente(self, node):
        grafo = self.graph.to_undirected(as_view=True) if self.graph.is_directed() else self.graph
        return theme.color_componente(min(nx.node_connected_component(grafo, node)))

    def _arista_seleccionada(self, u, v):
        if (u, v) in self.selected_edges or self.selected_edge == (u, v):
            return True
        if self.graph.is_directed():
            return False
        return (v, u) in self.selected_edges or self.selected_edge == (v, u)

    def _estilo_arista(self, u, v):
        if self._arista_seleccionada(u, v):
            return {'color': theme.ARISTA_SELECCIONADA, 'ancho': 4.5}
        color = self.edge_colors.get((u, v))
        if color is not None:
            return {'color': color, 'ancho': 4.5}
        return {'color': theme.ARISTA, 'ancho': 2.2}

    def _dibujarAristas(self, graph, nodos, tamanos):
        rectas = [edge for edge in graph.edges() if not self._es_curva(*edge)]
        curvas = [edge for edge in graph.edges() if self._es_curva(*edge)]
        dirigido = graph.is_directed()

        for aristas, conexion in ((rectas, 'arc3'), (curvas, f'arc3,rad={RADIO_CURVA}')):
            if not aristas:
                continue
            estilos = [self._estilo_arista(u, v) for u, v in aristas]
            # Flechas y curvas solo aplican a dirigidos; en no dirigidos networkx
            # usa líneas simples y avisa si recibe estos parámetros.
            extra_flechas = dict(
                arrowstyle='-|>',
                arrowsize=18,
                connectionstyle=conexion,
                # Con el tamaño real de cada nodo, la flecha termina en su borde.
                nodelist=nodos,
                node_size=tamanos,
            ) if dirigido else {}
            nx.draw_networkx_edges(
                graph,
                pos=self.pos,
                edgelist=aristas,
                edge_color=[estilo['color'] for estilo in estilos],
                width=[estilo['ancho'] for estilo in estilos],
                arrows=dirigido,
                ax=self.ax,
                **extra_flechas,
            )
            nx.draw_networkx_edge_labels(
                graph,
                pos=self.pos,
                edge_labels={(u, v): f"{graph.edges[u, v].get('weight', 1):g}" for u, v in aristas},
                font_size=9,
                font_color=theme.ETIQUETA_PESO,
                rotate=False,
                bbox=dict(boxstyle='round,pad=0.25', facecolor='white', edgecolor=theme.BORDE_ETIQUETA, linewidth=0.8),
                connectionstyle=conexion,
                nodelist=nodos,
                node_size=tamanos,
                ax=self.ax,
            )

    def exportarImagen(self, ruta, resumen):
        title = self.fig.suptitle('Visualizador de Grafos - ADA', fontsize=14, fontweight='bold', y=0.98)
        summary_text = self.fig.text(
            0.02,
            0.02,
            resumen,
            fontsize=9,
            ha='left',
            va='bottom',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#ffffff', edgecolor='#cbd5e1', alpha=0.9),
        )
        try:
            self.fig.savefig(ruta, bbox_inches='tight', pad_inches=0.25, facecolor=theme.FONDO)
        finally:
            title.remove()
            summary_text.remove()
            self.canvas.draw_idle()

    # ── Documento ──────────────────────────────────────────────

    @property
    def hay_cambios(self):
        return self.model.to_dict() != self._snapshot_guardado

    @property
    def nombre_documento(self):
        return Path(self.ruta_actual).name if self.ruta_actual else self._nombre_sin_ruta

    def _marcarGuardado(self, ruta, nombre_sin_ruta="Sin título"):
        self.ruta_actual = ruta
        self._nombre_sin_ruta = nombre_sin_ruta
        self._snapshot_guardado = self.model.to_dict()

    def guardarEnJSON(self, ruta):
        """Guarda el grafo en 'ruta'. Propaga OSError para que la ventana lo informe."""
        GraphService.save_json(self.model, ruta)
        self._marcarGuardado(str(ruta))
        self.grafoCambiado.emit()
        self.mensaje.emit(f"Grafo guardado en {ruta}")

    def nuevoGrafo(self):
        self.model = GraphModel(self.model.graph_type)
        self.history.clear()
        self._descartarResultado()
        self.clearSelection()
        self.origen_arista = None
        self.component_nodes = set()
        self.visual_filter = 'all'
        self._marcarGuardado(None)
        self._refresh_after_change()

    def cargarJson(self, ruta, como_plantilla=False):
        """Carga un grafo. Con 'como_plantilla' no se asocia el archivo
        (guardar pedirá una ruta nueva en lugar de sobrescribirlo)."""
        try:
            loaded_model = GraphService.load_json(ruta)
        except FileNotFoundError:
            self.Alertas(f"No se encontró el archivo:\n{ruta}", titulo="Error al cargar")
            return False
        except (OSError, ValueError) as exc:
            self.Alertas(f"No se pudo cargar el grafo.\n{exc}", titulo="Error al cargar")
            return False

        self.model = loaded_model
        self.history.clear()
        self._descartarResultado()
        self.clearSelection()
        self.origen_arista = None
        if como_plantilla:
            self._marcarGuardado(None, nombre_sin_ruta=Path(ruta).stem)
        else:
            self._marcarGuardado(str(ruta))
        self.tipoGrafoCambiado.emit(self.model.graph_type)
        self._refresh_after_change()
        self.mensaje.emit(f"Grafo cargado: {Path(ruta).name}")
        return True

    def setAristaColor(self, listaAristas, color):
        # Se vacía el diccionario completo: en no dirigidos cada arista tiene
        # dos claves, (u, v) y (v, u), y ambas pueden venir de un resultado previo.
        self.edge_colors.clear()

        for nodo1, nodo2 in listaAristas:
            self.edge_colors[(nodo1, nodo2)] = color
            if not self.graph.is_directed():
                self.edge_colors[(nodo2, nodo1)] = color

        self.DibujarGrafo()

    def Limpiar(self):
        if self.graph.number_of_nodes() == 0:
            return
        self._checkpoint()
        self.model.clear()
        self.clearSelection()
        self.component_nodes = set()
        self._refresh_after_change()
        self.mensaje.emit("Lienzo limpio (Ctrl+Z para recuperarlo).")

    def eliminarNodo(self, node_id):
        if node_id not in self.graph:
            self.Alertas(f"El nodo {node_id} no existe.")
            return
        self._checkpoint()
        self.model.eliminar_nodo(node_id)
        self._refresh_after_change()
        self.mensaje.emit(f"Nodo {node_id} eliminado.")

    def eliminarArista(self, node1, node2):
        if not self.graph.has_edge(node1, node2):
            self.Alertas(f"La arista {node1} - {node2} no existe.")
            return
        self._checkpoint()
        self.model.eliminar_arista(node1, node2)
        self._refresh_after_change()
        self.mensaje.emit(f"Arista {node1} - {node2} eliminada.")

    def eliminarSeleccion(self):
        """Elimina, en un solo paso deshacible, todo lo seleccionado."""
        nodes = set(self.selected_nodes)
        if self.selected_node is not None:
            nodes.add(self.selected_node)
        edges = set(self.selected_edges)
        if self.selected_edge is not None:
            edges.add(self.selected_edge)

        nodes = {node for node in nodes if node in self.graph}
        edges = {edge for edge in edges if self.graph.has_edge(*edge)}
        if not nodes and not edges:
            return

        self._checkpoint()
        for u, v in edges:
            if self.graph.has_edge(u, v):
                self.model.eliminar_arista(u, v)
        for node in nodes:
            self.model.eliminar_nodo(node)

        self.clearSelection()
        self._refresh_after_change()
        self.mensaje.emit(f"Eliminados: {len(nodes)} nodo(s), {len(edges)} arista(s).")

    def actualizarPesoArista(self, node1, node2, nuevo_peso):
        if not self.graph.has_edge(node1, node2):
            self.Alertas(f"La arista {node1} - {node2} no existe.")
            return
        if self.graph.edges[node1, node2].get('weight', 1) == nuevo_peso:
            return
        self._checkpoint()
        self.model.update_edge_weight(node1, node2, nuevo_peso)
        self._refresh_after_change()
        self.mensaje.emit(f"Peso de {node1} - {node2} actualizado a {nuevo_peso}.")

    def moverNodo(self, node_id, posicion):
        self._checkpoint(invalida_resultado=False)
        self.model.set_node_position(node_id, posicion)
        self._refresh_after_change()
