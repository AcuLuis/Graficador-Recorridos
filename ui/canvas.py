import math

import networkx as nx
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from core.graph_model import GraphModel
from core.graph_service import GraphService
from core.history import History

COLOR_ARISTA = '#2c3e50'
PALETA_COMPONENTES = ['#3498db', '#2ecc71', '#9b59b6', '#f39c12', '#e74c3c', '#1abc9c', '#34495e', '#e84393']


class Lienzo:
    def __init__(self, main_window):
        self.main_window = main_window
        self.model = GraphModel()
        self.dragging_node = None
        self.drag_start = None
        self.selected_node = None
        self.selected_edge = None
        self.selected_nodes = set()
        self.selected_edges = set()
        self.analysis_highlighted_nodes = {}
        self.component_nodes = set()
        self.is_panning = False
        self.pan_origin = None
        self.pan_start_px = None
        self.visual_filter = 'all'
        self.history = History()
        # Estado previo al arrastre; se registra solo si el nodo realmente se mueve.
        self._drag_snapshot = None

        # Figure (no pyplot): evita el estado global de pyplot dentro de Qt.
        self.fig = Figure(figsize=(8.5, 5.8))
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot()
        self.fig.patch.set_facecolor('#f5f7fa')
        self.ax.set_facecolor('#f5f7fa')
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.ax.set_position([0, 0, 1, 1])
        self.cid = self.canvas.mpl_connect('button_press_event', self.MouseClick)
        self.motion_cid = self.canvas.mpl_connect('motion_notify_event', self.MouseMove)
        self.release_cid = self.canvas.mpl_connect('button_release_event', self.MouseRelease)
        self.scroll_cid = self.canvas.mpl_connect('scroll_event', self.MouseWheel)
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

    # Los límites se leen siempre de los ejes para que el zoom/pan de la
    # toolbar de matplotlib y el zoom propio no se pisen entre sí.
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

    def cambiarTipoGrafo(self, tipo):
        """Empieza un grafo vacío del tipo indicado (se puede deshacer)."""
        self._checkpoint()
        self.model.clear()
        self.model.set_graph_type(tipo)
        self.clearSelection()
        self.component_nodes = set()
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
        self.main_window.clearAlgorithmResult()

    def Deshacer(self):
        self._restaurar(self.history.undo(self.model.to_dict()))

    def Rehacer(self):
        self._restaurar(self.history.redo(self.model.to_dict()))

    def _restaurar(self, snapshot):
        if snapshot is None:
            return
        self.model.load_from_dict(snapshot)
        self._descartarResultado()
        self.main_window.syncTipoGrafo(self.model.graph_type)
        self._refresh_after_change()

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
        self.selected_nodes = {node for node in self.selected_nodes if node in graph}
        self.selected_edges = {edge for edge in self.selected_edges if graph.has_edge(*edge)}

    def _refresh_after_change(self):
        """Limpia selección inválida y refresca el lienzo y los paneles."""
        self._prune_selection()
        self.DibujarGrafo()
        self.main_window.updateGraphStats()
        self.main_window.updateSelectionInfo(self.selected_node, self.selected_edge)

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

    def Alertas(self, mensaje, titulo="Elemento no encontrado"):
        alerta = QMessageBox()
        alerta.setIcon(QMessageBox.Icon.Warning)
        alerta.setText(titulo)
        alerta.setInformativeText(mensaje)
        alerta.setWindowTitle("Alerta")
        alerta.exec()

    def alertaConfirmacion(self, mensaje):
        alerta = QMessageBox()
        alerta.setIcon(QMessageBox.Icon.Warning)
        alerta.setText(mensaje)
        alerta.setWindowTitle('Confirmación requerida')
        btnSi = alerta.addButton('Sí', QMessageBox.ButtonRole.YesRole)
        alerta.addButton('Cancelar', QMessageBox.ButtonRole.NoRole)
        alerta.exec()
        return alerta.clickedButton() == btnSi

    def MouseClick(self, event):
        if event.xdata is None or event.ydata is None:
            return

        # Si la toolbar de matplotlib está en modo zoom/pan, el clic es suyo.
        toolbar = getattr(self.main_window, 'toolbar', None)
        if toolbar is not None and toolbar.mode != '':
            return

        if event.button == 3:
            clicked_node = self._find_node_at_position(event.xdata, event.ydata)
            if clicked_node is not None:
                self.eliminarNodo(clicked_node)
            return

        if event.button == 2:
            self.is_panning = True
            self.pan_origin = self.current_xlim + self.current_ylim
            # Se guardan píxeles: las coordenadas de datos cambian mientras la vista se mueve.
            self.pan_start_px = (event.x, event.y)
            return

        if self.main_window.dibNodoIsSelected():
            node_id = 1 if len(self.graph.nodes()) == 0 else max(self.graph.nodes()) + 1
            self._checkpoint()
            self.model.add_node(node_id, (event.xdata, event.ydata))
            self.clearSelection()
            self._refresh_after_change()
            return

        clicked_node = self._find_node_at_position(event.xdata, event.ydata)
        if clicked_node is not None:
            if event.key in ('control', 'shift'):
                if clicked_node in self.selected_nodes:
                    self.selected_nodes.remove(clicked_node)
                else:
                    self.selected_nodes.add(clicked_node)
                self.selected_node = clicked_node if clicked_node in self.selected_nodes else None
                self.selected_edge = None
                self.dragging_node = None
                self.DibujarGrafo()
                self.main_window.updateSelectionInfo()
                return

            self.selected_nodes.clear()
            self.selected_edges.clear()
            self.selected_node = clicked_node
            self.selected_edge = None
            self.dragging_node = clicked_node
            self.drag_start = (event.xdata, event.ydata)
            self._drag_snapshot = self.model.to_dict()
            self.DibujarGrafo()
            self.main_window.updateSelectionInfo(self.selected_node, self.selected_edge)
            return

        clicked_edge = self._find_edge_at_position(event.xdata, event.ydata)
        if clicked_edge is not None:
            if event.key in ('control', 'shift'):
                if clicked_edge in self.selected_edges:
                    self.selected_edges.remove(clicked_edge)
                else:
                    self.selected_edges.add(clicked_edge)
                self.selected_edge = clicked_edge if clicked_edge in self.selected_edges else None
                self.selected_node = None
                self.dragging_node = None
                self.DibujarGrafo()
                self.main_window.updateSelectionInfo()
                return

            self.selected_nodes.clear()
            self.selected_edges.clear()
            self.selected_edge = clicked_edge
            self.selected_node = None
            self.dragging_node = None
            self.DibujarGrafo()
            self.main_window.updateSelectionInfo(self.selected_node, self.selected_edge)
            return

        self.clearSelection()
        self.DibujarGrafo()
        self.main_window.updateSelectionInfo(self.selected_node, self.selected_edge)

    def _find_node_at_position(self, x, y):
        for node_id, position in self.pos.items():
            if abs(x - position[0]) <= 0.05 and abs(y - position[1]) <= 0.05:
                return node_id
        return None

    def _find_edge_at_position(self, x, y):
        threshold = 0.05
        for edge in self.graph.edges():
            if edge[0] in self.pos and edge[1] in self.pos:
                dist = self._distance_to_segment((x, y), self.pos[edge[0]], self.pos[edge[1]])
                if dist <= threshold:
                    return edge
        return None

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
        if self.is_panning and self.pan_origin is not None and self.pan_start_px is not None:
            x0, x1, y0, y1 = self.pan_origin
            bbox = self.ax.bbox
            dx = (event.x - self.pan_start_px[0]) * (x1 - x0) / bbox.width
            dy = (event.y - self.pan_start_px[1]) * (y1 - y0) / bbox.height

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
        self.DibujarGrafo()

    def MouseRelease(self, event):
        if self.dragging_node is not None and self._drag_snapshot is None:
            # Hubo arrastre: la posición mostrada en el panel cambió.
            self.main_window.updateSelectionInfo(self.selected_node, self.selected_edge)
        self._drag_snapshot = None
        self.dragging_node = None
        self.drag_start = None
        self.is_panning = False
        self.pan_origin = None
        self.pan_start_px = None

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

    def resetView(self):
        self.current_xlim = [0, 1]
        self.current_ylim = [0, 1]
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
        self.main_window.updateGraphStats()

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
                self.main_window.updateGraphStats()
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

    def DibujarGrafo(self):
        visible_graph = self._get_visible_graph()
        edge_labels = nx.get_edge_attributes(visible_graph, 'weight')

        xlim, ylim = self.current_xlim, self.current_ylim
        self.ax.clear()
        self.current_xlim = xlim
        self.current_ylim = ylim
        self.ax.axis('off')

        if visible_graph.is_directed():
            components = nx.weakly_connected_components(visible_graph)
        else:
            components = nx.connected_components(visible_graph)

        component_colors = {}
        for index, component in enumerate(components):
            color = PALETA_COMPONENTES[index % len(PALETA_COMPONENTES)]
            for node in component:
                component_colors[node] = color

        node_colors = []
        node_sizes = []
        node_edgecolors = []
        for node in visible_graph.nodes():
            if node in self.selected_nodes or node == self.selected_node:
                node_colors.append('#e67e22')
                node_sizes.append(1000)
                node_edgecolors.append('#d35400')
            elif visible_graph.degree(node) == 0:
                node_colors.append('#f39c12')
                node_sizes.append(900)
                node_edgecolors.append('#d68910')
            elif node in self.analysis_highlighted_nodes:
                node_colors.append(component_colors.get(node, '#3498db'))
                node_sizes.append(900)
                node_edgecolors.append('#8e44ad')
            else:
                node_colors.append(component_colors.get(node, '#3498db'))
                node_sizes.append(700)
                node_edgecolors.append('#2980b9')

        edge_colors_draw = []
        edge_widths = []
        for edge in visible_graph.edges():
            selected = edge in self.selected_edges or (
                self.selected_edge is not None and (
                    edge == self.selected_edge or edge == (self.selected_edge[1], self.selected_edge[0])
                )
            )
            edge_colors_draw.append('#e67e22' if selected else self.edge_colors.get(edge, COLOR_ARISTA))
            edge_widths.append(4.0 if selected else 2.5)

        nx.draw_networkx_nodes(
            visible_graph,
            pos=self.pos,
            node_color=node_colors,
            node_size=node_sizes,
            edgecolors=node_edgecolors,
            linewidths=2,
            ax=self.ax,
        )

        nx.draw_networkx_edges(
            visible_graph,
            pos=self.pos,
            ax=self.ax,
            edge_color=edge_colors_draw,
            width=edge_widths,
            arrows=visible_graph.is_directed(),
        )

        nx.draw_networkx_labels(
            visible_graph,
            pos=self.pos,
            labels={node: str(node) for node in visible_graph.nodes()},
            font_size=11,
            font_color='white',
            font_weight='bold',
            ax=self.ax,
        )

        nx.draw_networkx_edge_labels(
            visible_graph,
            pos=self.pos,
            edge_labels=edge_labels,
            ax=self.ax,
            font_size=10,
            font_color='#e74c3c',
        )

        self.canvas.draw_idle()

    def GuardarIMG(self):
        file_path, _ = QFileDialog.getSaveFileName(self.main_window, 'Guardar Imagen', '', 'PNG Files (*.png);;All Files (*)')
        if file_path:
            title = self.fig.suptitle('Visualizador de Grafos - ADA', fontsize=14, fontweight='bold', y=0.98)
            summary = self.main_window.buildGraphSummaryText()
            summary_text = self.fig.text(
                0.02,
                0.02,
                summary,
                fontsize=9,
                ha='left',
                va='bottom',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#ffffff', edgecolor='#cbd5e1', alpha=0.9),
            )
            try:
                self.fig.savefig(file_path, bbox_inches='tight', pad_inches=0.25, facecolor='#f5f7fa')
            finally:
                title.remove()
                summary_text.remove()

    def guardarEnJSON(self):
        ruta, _ = QFileDialog.getSaveFileName(self.main_window, 'Guardar Grafo', '', 'JSON Files (*.json);;All Files (*)')
        if ruta:
            GraphService.save_json(self.model, ruta)

    def cargarJson(self, ruta_archivo=None):
        ruta = ruta_archivo
        if not ruta:
            ruta, _ = QFileDialog.getOpenFileName(self.main_window, 'Cargar Grafo', '', 'JSON Files (*.json);;All Files (*)')

        if not ruta:
            return False

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
        self.main_window.syncTipoGrafo(self.model.graph_type)
        self._refresh_after_change()
        return True

    def setAristaColor(self, listaAristas, color):
        for edge in self.graph.edges():
            self.edge_colors[edge] = COLOR_ARISTA

        for nodo1, nodo2 in listaAristas:
            self.edge_colors[(nodo1, nodo2)] = color
            if not self.graph.is_directed():
                self.edge_colors[(nodo2, nodo1)] = color

        self.DibujarGrafo()
        self.main_window.updateGraphStats()

    def Limpiar(self):
        if self.graph.number_of_nodes() == 0:
            return
        self._checkpoint()
        self.model.clear()
        self.clearSelection()
        self.component_nodes = set()
        self._refresh_after_change()

    def eliminarNodo(self, node_id):
        if node_id not in self.graph:
            self.Alertas(f"El nodo {node_id} no existe.")
            return
        self._checkpoint()
        self.model.eliminar_nodo(node_id)
        self._refresh_after_change()

    def eliminarArista(self, node1, node2):
        if not self.graph.has_edge(node1, node2):
            self.Alertas(f"La arista {node1} - {node2} no existe.")
            return
        self._checkpoint()
        self.model.eliminar_arista(node1, node2)
        self._refresh_after_change()

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

    def actualizarPesoArista(self, node1, node2, nuevo_peso):
        if not self.graph.has_edge(node1, node2):
            self.Alertas(f"La arista {node1} - {node2} no existe.")
            return
        if self.graph.edges[node1, node2].get('weight', 1) == nuevo_peso:
            return
        self._checkpoint()
        self.model.update_edge_weight(node1, node2, nuevo_peso)
        self._refresh_after_change()

    def moverNodo(self, node_id, posicion):
        self._checkpoint(invalida_resultado=False)
        self.model.set_node_position(node_id, posicion)
        self._refresh_after_change()
