import sys
import json
import ast
import math
import traceback
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeySequence, QAction, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QRadioButton, QGroupBox,
    QMessageBox, QFileDialog, QDockWidget, QScrollArea,
    QDialog, QLineEdit, QSizePolicy
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from Arista import MiDialogo
from DialogNodo import DialogoNodo
from algorithms_service import AlgorithmsService
from graph_model import GraphModel
from graph_service import GraphService

DATOS_PRUEBA = Path(__file__).resolve().parent / "datos_prueba.json"


def manejarExcepcionNoCapturada(exc_type, exc_value, exc_tb):
    """Muestra el error en vez de cerrar la app.

    Con el excepthook por defecto, PyQt6 aborta el proceso ante cualquier
    excepción no capturada dentro de un slot.
    """
    traceback.print_exception(exc_type, exc_value, exc_tb)
    if QApplication.instance() is None:
        return
    QMessageBox.critical(
        None,
        "Error inesperado",
        f"Ocurrió un error y la operación no se completó:\n\n{exc_type.__name__}: {exc_value}",
    )


class Lienzo:
    def __init__(self, main_window):
        self.main_window = main_window
        self.model = GraphModel()
        self.graph = self.model.graph
        self.edge_colors = self.model.edge_colors
        self.edge_weights = self.model.edge_weights
        self.pos = self.model.pos
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
        self.historial = []

        self.fig, self.ax = plt.subplots(figsize=(8.5, 5.8))
        self.fig.patch.set_facecolor('#f5f7fa')
        self.ax.set_facecolor('#f5f7fa')
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.ax.set_position([0, 0, 1, 1])
        self.cid = self.fig.canvas.mpl_connect('button_press_event', self.MouseClick)
        self.motion_cid = self.fig.canvas.mpl_connect('motion_notify_event', self.MouseMove)
        self.release_cid = self.fig.canvas.mpl_connect('button_release_event', self.MouseRelease)
        self.scroll_cid = self.fig.canvas.mpl_connect('scroll_event', self.MouseWheel)
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.axis('off')

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

    def setTipoGrafo(self, tipo):
        self.model.set_graph_type(tipo)
        self.historial.clear()
        self.clearAnalysisHighlights()
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
        """Sincroniza alias del modelo, limpia selección inválida y refresca UI."""
        self.graph = self.model.graph
        self.pos = self.model.pos
        self.edge_colors = self.model.edge_colors
        self.edge_weights = self.model.edge_weights
        self._prune_selection()
        self.DibujarGrafo()
        self.main_window.updateGraphStats()
        self.main_window.updateSelectionInfo(self.selected_node, self.selected_edge)

    def DibujarArista(self, posNodo1, posNodo2, peso=1):
        if posNodo1 in self.graph.nodes() and posNodo2 in self.graph.nodes():
            self.model.add_edge(posNodo1, posNodo2, peso=peso)
            self.graph = self.model.graph
            self.edge_colors = self.model.edge_colors
            self.edge_weights = self.model.edge_weights
            self.historial.append(('arista', (posNodo1, posNodo2)))
            self.DibujarGrafo()
            self.main_window.updateGraphStats()
        else:
            msg = "Los nodos no se encuentran."
            if posNodo1 not in self.graph.nodes():
                msg = f"El nodo {posNodo1} no se encuentra."
            elif posNodo2 not in self.graph.nodes():
                msg = f"El nodo {posNodo2} no se encuentra."
            self.Alertas(msg)

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
        btnNo = alerta.addButton('Cancelar', QMessageBox.ButtonRole.NoRole)
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
            if event.xdata is not None and event.ydata is not None:
                node_id = 1 if len(self.graph.nodes()) == 0 else max(self.graph.nodes()) + 1
                self.model.add_node(node_id, (event.xdata, event.ydata))
                self.graph = self.model.graph
                self.pos = self.model.pos
                self.historial.append(('nodo', node_id))
                self.selected_node = None
                self.selected_edge = None
                self.selected_nodes.clear()
                self.selected_edges.clear()
                self.DibujarGrafo()
                self.main_window.updateGraphStats()
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

        self.selected_node = None
        self.selected_edge = None
        self.selected_nodes.clear()
        self.selected_edges.clear()
        self.dragging_node = None
        self.DibujarGrafo()
        self.main_window.updateSelectionInfo(self.selected_node, self.selected_edge)

    def _find_node_at_position(self, x, y):
        for node_id, position in self.pos.items():
            nx_pos = position[0]
            ny_pos = position[1]
            if abs(x - nx_pos) <= 0.05 and abs(y - ny_pos) <= 0.05:
                return node_id
        return None

    def _find_edge_at_position(self, x, y):
        threshold = 0.05
        for edge in self.graph.edges():
            if edge[0] in self.pos and edge[1] in self.pos:
                p1 = self.pos[edge[0]]
                p2 = self.pos[edge[1]]
                dist = self._distance_to_segment((x, y), p1, p2)
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
            self.fig.canvas.draw_idle()
            return

        if event.xdata is None or event.ydata is None or self.dragging_node is None:
            return

        self.model.set_node_position(self.dragging_node, (event.xdata, event.ydata))
        self.graph = self.model.graph
        self.pos = self.model.pos
        self.DibujarGrafo()

    def MouseRelease(self, event):
        self.dragging_node = None
        self.drag_start = None
        self.is_panning = False
        self.pan_origin = None
        self.pan_start_px = None

    def MouseWheel(self, event):
        if event.xdata is None or event.ydata is None:
            return

        zoom_factor = 1.1 if event.step > 0 else 1 / 1.1
        x_range = self.current_xlim[1] - self.current_xlim[0]
        y_range = self.current_ylim[1] - self.current_ylim[0]

        current_x0, current_x1 = self.current_xlim
        current_y0, current_y1 = self.current_ylim

        x_ratio = (event.xdata - current_x0) / x_range
        y_ratio = (event.ydata - current_y0) / y_range

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

        self.ax.set_xlim(*self.current_xlim)
        self.ax.set_ylim(*self.current_ylim)
        self.fig.canvas.draw_idle()

    def resetView(self):
        self.current_xlim = [0, 1]
        self.current_ylim = [0, 1]
        self.ax.set_xlim(*self.current_xlim)
        self.ax.set_ylim(*self.current_ylim)
        self.fig.canvas.draw_idle()

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

        if isinstance(self.graph, nx.DiGraph):
            components = list(nx.weakly_connected_components(self.graph))
        else:
            components = list(nx.connected_components(self.graph))

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
            visible_graph = self.graph.subgraph(visible_nodes).copy()
        elif self.visual_filter == 'component':
            visible_nodes = list(self.component_nodes) if self.component_nodes else list(self.graph.nodes())
            visible_graph = self.graph.subgraph(visible_nodes).copy()
        else:
            visible_graph = self.graph.copy()

        if visible_graph.number_of_nodes() == 0:
            if isinstance(self.graph, nx.DiGraph):
                return nx.DiGraph()
            return nx.Graph()

        return visible_graph

    def zoomIn(self):
        self._apply_zoom(1.15)

    def zoomOut(self):
        self._apply_zoom(1 / 1.15)

    def _apply_zoom(self, zoom_factor):
        center_x = (self.current_xlim[0] + self.current_xlim[1]) / 2
        center_y = (self.current_ylim[0] + self.current_ylim[1]) / 2

        x_range = max(0.05, (self.current_xlim[1] - self.current_xlim[0]) / zoom_factor)
        y_range = max(0.05, (self.current_ylim[1] - self.current_ylim[0]) / zoom_factor)

        self.current_xlim = [center_x - x_range / 2, center_x + x_range / 2]
        self.current_ylim = [center_y - y_range / 2, center_y + y_range / 2]

        self.ax.set_xlim(*self.current_xlim)
        self.ax.set_ylim(*self.current_ylim)
        self.fig.canvas.draw_idle()

    def DibujarGrafo(self):
        self.graph = self.model.graph
        self.pos = self.model.pos
        self.edge_colors = self.model.edge_colors
        self.edge_weights = self.model.edge_weights

        visible_graph = self._get_visible_graph()
        edge_labels = nx.get_edge_attributes(visible_graph, 'weight')

        xlim, ylim = self.current_xlim, self.current_ylim
        self.ax.clear()
        self.current_xlim = xlim
        self.current_ylim = ylim
        self.ax.axis('off')

        palette = ['#3498db', '#2ecc71', '#9b59b6', '#f39c12', '#e74c3c', '#1abc9c', '#34495e', '#e84393']

        if isinstance(visible_graph, nx.DiGraph):
            components = list(nx.weakly_connected_components(visible_graph))
        else:
            components = list(nx.connected_components(visible_graph))

        component_colors = {}
        for index, component in enumerate(components):
            color = palette[index % len(palette)]
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
            edge_colors_draw.append('#e67e22' if selected else self.edge_colors.get(edge, '#2c3e50'))
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
            arrows=isinstance(visible_graph, nx.DiGraph),
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

        self.fig.canvas.draw_idle()

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
        self.historial.clear()
        self.clearAnalysisHighlights()
        self.clearSelection()
        self.main_window.syncTipoGrafo(self.model.graph_type)
        self._refresh_after_change()
        return True

    def setAristaColor(self, listaAristas, color):
        for edge in self.model.graph.edges():
            self.model.edge_colors[edge] = '#2c3e50'

        for tupla in listaAristas:
            nodo1, nodo2 = tupla
            self.model.edge_colors[(nodo1, nodo2)] = color
            if not isinstance(self.model.graph, nx.DiGraph):
                self.model.edge_colors[(nodo2, nodo1)] = color

        self.edge_colors = self.model.edge_colors
        self.DibujarGrafo()
        self.main_window.updateGraphStats()

    def Deshacer(self):
        if not self.historial:
            return
            
        ultimo = self.historial.pop()
        tipo, dato = ultimo
        
        if tipo == 'nodo':
            try:
                self.model.eliminar_nodo(dato)
            except ValueError:
                pass
        elif tipo == 'arista':
            u, v = dato
            try:
                self.model.eliminar_arista(u, v)
            except ValueError:
                pass

        self._refresh_after_change()

    def Limpiar(self):
        self.model.clear()
        self.historial.clear()
        self.clearAnalysisHighlights()
        self.clearSelection()
        self.component_nodes = set()
        self._refresh_after_change()

    def eliminarNodo(self, node_id):
        try:
            self.model.eliminar_nodo(node_id)
        except ValueError as exc:
            self.Alertas(str(exc))
            return
        self._refresh_after_change()

    def eliminarArista(self, node1, node2):
        try:
            self.model.eliminar_arista(node1, node2)
        except ValueError as exc:
            self.Alertas(str(exc))
            return
        self._refresh_after_change()

    def actualizarPesoArista(self, node1, node2, nuevo_peso):
        try:
            self.model.update_edge_weight(node1, node2, nuevo_peso)
        except ValueError as exc:
            self.Alertas(str(exc))
            return
        self._refresh_after_change()


class PanelVista(QWidget):
    def __init__(self):
        super().__init__()
        self.ancho = 800
        self.alto = 600
        
        cabecera = QFrame()
        grafoUI = QGroupBox("Vista Grafo")
        
        cbzAlgoritmo = QGroupBox("Algoritmo Actual")
        cbzAlgoritmo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lblAlgoritmo = QLabel("Nombre:")
        self.lblTipo = QLabel("")
        
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.lblTipo.setFont(font)
        self.lblTipo.setStyleSheet("color: #2c3e50;")
        
        cbzAlgoritmo_layout = QHBoxLayout()
        cbzAlgoritmo_layout.addWidget(lblAlgoritmo)
        cbzAlgoritmo_layout.addWidget(self.lblTipo)
        cbzAlgoritmo_layout.addStretch()
        cbzAlgoritmo.setLayout(cbzAlgoritmo_layout)

        cbzTipoGrafo = QGroupBox("Tipo de Grafo")
        cbzTipoGrafo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.rbDirigido = QRadioButton("Grafo Dirigido")
        self.rbNoDirigido = QRadioButton("Grafo No Dirigido")
        self.rbNoDirigido.setChecked(True)
        self.rbNoDirigido.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.rbDirigido.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        cbzTipoGrafo_layout = QHBoxLayout()
        cbzTipoGrafo_layout.addWidget(self.rbNoDirigido)
        cbzTipoGrafo_layout.addWidget(self.rbDirigido)
        cbzTipoGrafo_layout.addStretch()
        cbzTipoGrafo.setLayout(cbzTipoGrafo_layout)

        cbzBotones = QGroupBox("Herramientas de Edición")
        cbzBotones.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.rbDibNodo = QRadioButton('Dibujar Nodo')
        self.rbDibArista = QRadioButton('Dibujar Arista')
        self.btnDibujar = QPushButton('Puntos arista')
        self.btnEliminarNodo = QPushButton('Eliminar Nodo')
        self.btnEliminarArista = QPushButton('Eliminar Arista')
        self.btnEditarPesoArista = QPushButton('Editar peso')
        self.btnZoomIn = QPushButton('Zoom +')
        self.btnZoomOut = QPushButton('Zoom -')
        self.btnResetVista = QPushButton('Restaurar vista')
        self.btnLimpiar = QPushButton('Limpiar lienzo')
        self.btnMostrarTodo = QPushButton('Mostrar todo')
        self.btnOcultarAislados = QPushButton('Ocultar aislados')
        self.btnComponenteActual = QPushButton('Componente actual')
        
        self.rbDibNodo.setChecked(True)
        self.btnDibujar.setEnabled(False)
        
        cbzBotones_layout = QGridLayout()
        cbzBotones_layout.setHorizontalSpacing(8)
        cbzBotones_layout.setVerticalSpacing(8)

        botones = [
            self.rbDibNodo,
            self.rbDibArista,
            self.btnDibujar,
            self.btnEliminarNodo,
            self.btnEliminarArista,
            self.btnEditarPesoArista,
            self.btnZoomIn,
            self.btnZoomOut,
            self.btnResetVista,
            self.btnLimpiar,
            self.btnMostrarTodo,
            self.btnOcultarAislados,
            self.btnComponenteActual,
        ]

        for index, boton in enumerate(botones):
            fila = index // 6
            columna = index % 6
            cbzBotones_layout.addWidget(boton, fila, columna)

        cbzBotones_layout.setColumnStretch(0, 1)
        cbzBotones_layout.setColumnStretch(1, 1)
        cbzBotones_layout.setColumnStretch(2, 1)
        cbzBotones_layout.setColumnStretch(3, 1)
        cbzBotones_layout.setColumnStretch(4, 1)
        cbzBotones_layout.setColumnStretch(5, 1)
        cbzBotones.setLayout(cbzBotones_layout)

        top_bar_layout = QHBoxLayout()
        top_bar_layout.addWidget(cbzTipoGrafo)
        top_bar_layout.addWidget(cbzAlgoritmo)

        cabecera_layout = QVBoxLayout()
        cabecera_layout.setContentsMargins(4, 4, 4, 4)
        cabecera_layout.setSpacing(4)
        cabecera_layout.addLayout(top_bar_layout)
        cabecera_layout.addWidget(cbzBotones)
        cabecera.setLayout(cabecera_layout)
        cabecera.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self.lienzo = Lienzo(self)
        self.toolbar = NavigationToolbar(self.lienzo.fig.canvas, self)
        self.lienzo.fig.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        grafoUI_layout = QVBoxLayout()
        grafoUI_layout.addWidget(self.toolbar)
        grafoUI_layout.addWidget(self.lienzo.fig.canvas, stretch=1)
        grafoUI.setLayout(grafoUI_layout)
        grafoUI.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.setMinimumSize(self.ancho, self.alto)

        main_layout = QVBoxLayout()
        main_layout.addWidget(cabecera)
        main_layout.addWidget(grafoUI, stretch=1)
        main_layout.setStretch(0, 0)
        main_layout.setStretch(1, 1)
        self.setLayout(main_layout)

        # Conexiones
        # Basta con uno: los radios son exclusivos y 'toggled' solo se emite si el estado cambia.
        self.rbDirigido.toggled.connect(self.setTipoGrafo)
        self.rbDibArista.toggled.connect(self.onRadioButtonToggled)
        self.btnDibujar.clicked.connect(self.PideNodos)
        self.btnEliminarNodo.clicked.connect(self.eliminarNodo)
        self.btnEliminarArista.clicked.connect(self.eliminarArista)
        self.btnEditarPesoArista.clicked.connect(self.editarPesoArista)
        self.btnZoomIn.clicked.connect(self.lienzo.zoomIn)
        self.btnZoomOut.clicked.connect(self.lienzo.zoomOut)
        self.btnResetVista.clicked.connect(self.lienzo.resetView)
        self.btnLimpiar.clicked.connect(self.LimpiarLienzo)
        self.btnMostrarTodo.clicked.connect(lambda: self.lienzo.setVisualFilter('all'))
        self.btnOcultarAislados.clicked.connect(lambda: self.lienzo.setVisualFilter('hide_isolated'))
        self.btnComponenteActual.clicked.connect(self.focusComponent)

    def setTipoGrafo(self, _checked=None):
        tipo = "Directed" if self.rbDirigido.isChecked() else "Undirected"
        if tipo == self.lienzo.model.graph_type:
            return

        if self.lienzo.graph.number_of_nodes() > 0:
            if not self.lienzo.alertaConfirmacion('Se borrará tu avance. \n ¿Estás seguro de cambiar el tipo de grafo?'):
                self.syncTipoGrafo(self.lienzo.model.graph_type)
                return
            self.lienzo.Limpiar()

        self.lienzo.setTipoGrafo(tipo)

    def syncTipoGrafo(self, tipo):
        """Marca el radio que corresponde a 'tipo' sin disparar setTipoGrafo."""
        for radio in (self.rbDirigido, self.rbNoDirigido):
            radio.blockSignals(True)
        if tipo == "Directed":
            self.rbDirigido.setChecked(True)
        else:
            self.rbNoDirigido.setChecked(True)
        for radio in (self.rbDirigido, self.rbNoDirigido):
            radio.blockSignals(False)

    def onRadioButtonToggled(self, state):
        if state:
            self.lienzo.fig.canvas.mpl_disconnect(self.lienzo.cid)
            self.btnDibujar.setEnabled(True)
        else:
            self.lienzo.fig.canvas.mpl_disconnect(self.lienzo.cid)
            self.lienzo.cid = self.lienzo.fig.canvas.mpl_connect('button_press_event', self.lienzo.MouseClick)
            self.btnDibujar.setEnabled(False)

    def dibNodoIsSelected(self):
        return not self.btnDibujar.isEnabled()

    def updateGraphStats(self):
        parent = self.parent()
        if parent is not None and hasattr(parent, 'updateGraphStats'):
            parent.updateGraphStats()

    def updateSelectionInfo(self, selected_node=None, selected_edge=None):
        parent = self.parent()
        if parent is not None and hasattr(parent, 'updateSelectionInfo'):
            parent.updateSelectionInfo(selected_node, selected_edge)

    def PideNodos(self):
        dialogo = MiDialogo(self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            v1, v2, v3 = dialogo.valor1, dialogo.valor2, dialogo.valor3
            if v1 and v2 and v3:
                self.lienzo.DibujarArista(int(v1), int(v2), int(v3))
            else:
                self.lienzo.Alertas("Ingresar valores correctos")

    def LimpiarLienzo(self):
        self.lblTipo.setText("")
        self.lienzo.Limpiar()

    def focusComponent(self):
        if self.lienzo.selected_node is None:
            self.lienzo.Alertas("Primero selecciona un nodo para enfocar su componente.")
            return

        if not self.lienzo.focusCurrentComponent():
            self.lienzo.Alertas("No se pudo encontrar el componente del nodo seleccionado.")

    def eliminarNodo(self):
        dialogN = DialogoNodo("Eliminar Nodo", "Ingresa el ID del Nodo a eliminar:", self)
        if dialogN.exec() == QDialog.DialogCode.Accepted:
            try:
                self.lienzo.eliminarNodo(int(dialogN.valor1))
            except ValueError:
                self.lienzo.Alertas("El ID debe ser un número entero.")

    def eliminarArista(self):
        nodo1 = self.solicitarNodoSecundario("Eliminar Arista", "Ingresa el nodo origen:")
        if nodo1 is None:
            return

        nodo2 = self.solicitarNodoSecundario("Eliminar Arista", "Ingresa el nodo destino:")
        if nodo2 is None:
            return

        self.lienzo.eliminarArista(nodo1, nodo2)

    def editarPesoArista(self):
        if self.lienzo.selected_edge is None:
            self.lienzo.Alertas("Primero selecciona una arista en el grafo.")
            return

        u, v = self.lienzo.selected_edge
        peso_actual = self.lienzo.graph.edges[u, v].get('weight', 1)

        dialogo = MiDialogo(self)
        dialogo.setWindowTitle('Editar Peso de Arista')
        dialogo.btnGuardar.setText('Guardar Peso')
        dialogo.entrada1.setText(str(u))
        dialogo.entrada2.setText(str(v))
        dialogo.entrada1.setReadOnly(True)
        dialogo.entrada2.setReadOnly(True)
        dialogo.entrada3.setText(str(peso_actual))
        dialogo.entrada3.selectAll()
        dialogo.entrada3.setFocus()

        if dialogo.exec() == QDialog.DialogCode.Accepted:
            try:
                nuevo_peso = int(dialogo.valor3)
                self.lienzo.actualizarPesoArista(int(dialogo.valor1), int(dialogo.valor2), nuevo_peso)
            except ValueError:
                self.lienzo.Alertas("Ingresa un peso válido.")

    def solicitarNodoSecundario(self, titulo, mensaje):
        dialogN = DialogoNodo(titulo, mensaje, self)
        if dialogN.exec() == QDialog.DialogCode.Accepted:
            try:
                return int(dialogN.valor1)
            except ValueError:
                self.lienzo.Alertas("El ID debe ser un número entero.")
                return None
        return None
        
    def setNombreAlgoritmo(self, nombre):
        self.lblTipo.setText(nombre)


class Panel(QWidget):
    """Panel lateral para mostrar resultados de algoritmos y propiedades de selección."""
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.scrollarea = QScrollArea(self)
        self.scrollarea.setWidgetResizable(True)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(12, 12, 12, 12)
        self.scroll_layout.setSpacing(12)

        self.selection_label = QLabel("Selecciona un nodo o una arista para ver sus propiedades.")
        self.selection_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.selection_label.setWordWrap(True)

        self.stats_label = QLabel("Resumen del grafo:\nNodos: 0\nAristas: 0\nTipo: Grafo No Dirigido")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.stats_label.setWordWrap(True)

        self.view_label = QLabel("Vista actual: Todo")
        self.view_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.view_label.setWordWrap(True)

        self.content_label = QLabel("Ejecuta un algoritmo para ver los pasos.")
        self.content_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.content_label.setWordWrap(True)

        self.help_label = QLabel(
            "Ayuda rápida:\n"
            "• Click en el lienzo para crear nodos cuando está activo 'Dibujar Nodo'.\n"
            "• Ctrl/Shift + click para seleccionar varios nodos o aristas.\n"
            "• Botón central del mouse para desplazar la vista.\n"
            "• Usa 'Ocultar aislados' o 'Componente actual' para enfocar análisis."
        )
        self.help_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.help_label.setWordWrap(True)

        self.btnEditarSeleccion = QPushButton("Editar selección")
        self.btnEliminarSeleccion = QPushButton("Eliminar selección")
        self.btnLimpiarAnalisis = QPushButton("Limpiar análisis")
        self.btnEditarSeleccion.setEnabled(False)
        self.btnEliminarSeleccion.setEnabled(False)

        font = QFont()
        font.setPointSize(11)
        self.selection_label.setFont(font)

        mono_font = QFont("Consolas")
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        mono_font.setPointSize(11)
        self.content_label.setFont(mono_font)

        self.scroll_layout.addWidget(self.selection_label)
        self.scroll_layout.addWidget(self.btnEditarSeleccion)
        self.scroll_layout.addWidget(self.btnEliminarSeleccion)
        self.scroll_layout.addWidget(self.btnLimpiarAnalisis)
        self.scroll_layout.addWidget(self.help_label)
        self.scroll_layout.addWidget(self.stats_label)
        self.scroll_layout.addWidget(self.view_label)
        self.scroll_layout.addWidget(self.content_label)

        self.scrollarea.setWidget(self.scroll_content)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scrollarea)
        self.setLayout(layout)

    def setContent(self, newcontent):
        self.content_label.setText(newcontent)

    def setSelectionInfo(self, newcontent):
        self.selection_label.setText(newcontent)

    def setStats(self, newcontent):
        self.stats_label.setText(newcontent)

    def setViewInfo(self, newcontent):
        self.view_label.setText(newcontent)

    def clearSelectionInfo(self):
        self.selection_label.setText("Selecciona un nodo o una arista para ver sus propiedades.")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VISUALIZADOR DE GRAFOS - ADA")
        self.setMinimumSize(800, 600)

        self.setStyleSheet("""
            * { font-family: 'Segoe UI', 'Arial', sans-serif; }

            QMainWindow, QDialog, QWidget {
                background-color: #edf2f7;
                color: #1f2937;
            }

            /* ── Barra de menú ── */
            QMenuBar {
                background-color: #1a1a2e;
                color: #e8e8e8;
                padding: 3px 2px;
                font-size: 13px;
            }
            QMenuBar::item {
                background: transparent;
                padding: 6px 12px;
                border-radius: 5px;
            }
            QMenuBar::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4aa5df, stop:1 #2c8dd8);
                color: white;
            }
            QMenu {
                background-color: #ffffff;
                color: #1f2937;
                border: 1px solid #d4d9e0;
                border-radius: 8px;
                padding: 4px 0;
            }
            QMenu::item {
                padding: 6px 24px;
            }
            QMenu::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4aa5df, stop:1 #2c8dd8);
                color: white;
                border-radius: 4px;
            }

            /* ── Paneles y agrupaciones ── */
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #d1dae4;
                border-radius: 10px;
                margin-top: 12px;
                padding: 18px 12px 10px 12px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8fafc);
                color: #1f2937;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 2px 8px;
                color: #334155;
                background-color: #f8fafc;
                border-radius: 4px;
            }

            /* ── Radio buttons ── */
            QRadioButton {
                color: #1f2937;
                font-size: 13px;
                font-weight: bold;
                spacing: 6px;
                padding: 4px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #94a3b8;
                border-radius: 10px;
                background-color: #ffffff;
            }
            QRadioButton::indicator:checked {
                background-color: #3ea5e8;
                border-color: #2f8fce;
            }

            /* ── Botones ── */
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #49afd9, stop:1 #2a8fcc);
                color: white;
                border: 1px solid #247db7;
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                min-height: 32px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #58b9e6, stop:1 #2682c0);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #227bb0, stop:1 #1d6b9a);
            }
            QPushButton:disabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #d5dde6, stop:1 #c5cfdb);
                border-color: #b7c1ce;
                color: #7a8897;
            }

            /* ── Campos de texto ── */
            QLineEdit {
                background-color: #ffffff;
                color: #1f2937;
                border: 2px solid #cbd5e1;
                border-radius: 7px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }

            /* ── Panel lateral (dock) ── */
            QDockWidget {
                color: #1f2937;
                font-size: 13px;
            }
            QDockWidget::title {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2a3a, stop:1 #152238);
                color: white;
                padding: 8px 12px;
                font-weight: bold;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QDockWidget::close-button, QDockWidget::float-button {
                background: transparent;
                border: none;
                padding: 2px;
            }

            /* ── ScrollArea y contenido ── */
            QScrollArea {
                border: none;
                background-color: #f8fafc;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #f8fafc;
            }

            /* ── Labels ── */
            QLabel {
                color: #1f2937;
                font-size: 13px;
            }

            /* ── MessageBox y diálogos ── */
            QMessageBox {
                background-color: #ffffff;
            }
            QMessageBox QLabel {
                color: #1f2937;
                font-size: 13px;
            }
        """)

        # Configurar UI
        self.centralWidget = PanelVista()
        self.setCentralWidget(self.centralWidget)
        
        self.dock_widget = QDockWidget("Panel de Información", self)
        self.panel = Panel()
        self.panel.setMinimumWidth(300)
        self.dock_widget.setWidget(self.panel)
        self.dock_widget.setMaximumWidth(350)
        self.dock_widget.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_widget)

        self.setupMenuBar()
        self.setupShortcuts()
        self.panel.btnEditarSeleccion.clicked.connect(self.handleSelectionEdit)
        self.panel.btnEliminarSeleccion.clicked.connect(self.handleSelectionDelete)
        self.panel.btnLimpiarAnalisis.clicked.connect(self.clearAnalysisState)
        self.updateGraphStats()

    def setupMenuBar(self):
        menubar = self.menuBar()

        # Archivo
        menuArchivo = menubar.addMenu("&Archivo")
        
        btnGuardarImagen = QAction('Guardar Imagen', self)
        btnGuardarImagen.setShortcut('Ctrl+I')
        btnGuardarImagen.triggered.connect(self.centralWidget.lienzo.GuardarIMG)

        btnGuardarResumen = QAction('Guardar Resumen', self)
        btnGuardarResumen.triggered.connect(self.guardarResumen)
        
        btnGuardarJson = QAction('Guardar Grafo', self)
        btnGuardarJson.setShortcut('Ctrl+S')
        btnGuardarJson.triggered.connect(self.centralWidget.lienzo.guardarEnJSON)
        
        btnCargarJson = QAction('Cargar Grafo', self)
        btnCargarJson.setShortcut('Ctrl+O')
        btnCargarJson.triggered.connect(self.centralWidget.lienzo.cargarJson)
        
        menuArchivo.addAction(btnCargarJson)
        menuArchivo.addAction(btnGuardarJson)
        menuArchivo.addAction(btnGuardarImagen)
        menuArchivo.addAction(btnGuardarResumen)

        # Grafos
        menuGrafos = menubar.addMenu("&Grafos")
        
        btnGrafoPrueba = QAction('Cargar Grafo de Prueba', self)
        btnGrafoPrueba.triggered.connect(self.dibujaPruebaGrafo)
        menuGrafos.addAction(btnGrafoPrueba)
        
        btnLimpiar = QAction('Limpiar Selecciones', self)
        btnLimpiar.triggered.connect(self.limpiarSelecciones)
        menuGrafos.addAction(btnLimpiar)

        # Algoritmos
        menuAlgoritmos = menubar.addMenu("&Algoritmos")
        
        btnBFS = QAction('BFS - Búsqueda en anchura', self)
        btnBFS.triggered.connect(self.ejecutarBFS)
        menuAlgoritmos.addAction(btnBFS)
        
        btnDFS = QAction('DFS - Búsqueda en profundidad', self)
        btnDFS.triggered.connect(self.ejecutarDFS)
        menuAlgoritmos.addAction(btnDFS)
        
        btnKruskal = QAction('Kruskal - Árbol de expansión mínima', self)
        btnKruskal.triggered.connect(self.ejecutarKruskal)
        menuAlgoritmos.addAction(btnKruskal)

        btnCentralidad = QAction('Centralidad de grado', self)
        btnCentralidad.triggered.connect(self.ejecutarCentralidad)
        menuAlgoritmos.addAction(btnCentralidad)
        
        btnDIJS = QAction('Dijkstra - Camino más corto', self)
        btnDIJS.triggered.connect(self.ejecutarDijkstra)
        menuAlgoritmos.addAction(btnDIJS)

    def setupShortcuts(self):
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.centralWidget.lienzo.Deshacer)

    def dibujaPruebaGrafo(self):
        if self.centralWidget.lienzo.cargarJson(str(DATOS_PRUEBA)):
            self.centralWidget.setNombreAlgoritmo("Grafo de Prueba")

    def solicitarInicio(self):
        if not self.centralWidget.lienzo.graph.nodes():
            QMessageBox.warning(self, "Advertencia", "El grafo no tiene nodos.")
            return None
            
        dialogN = DialogoNodo("Inicio de Recorrido", "Ingresa el ID del Nodo de inicio:", self)
        if dialogN.exec() == QDialog.DialogCode.Accepted:
            try:
                return int(dialogN.valor1)
            except ValueError:
                QMessageBox.warning(self, "Error", "El ID debe ser un número entero.")
        return None

    def ejecutarBFS(self):
        inicio = self.solicitarInicio()
        if inicio is not None:
            res = AlgorithmsService.bfs(self.centralWidget.lienzo.graph, inicio)
            self.panel.setContent(res["content"])
            if res["aristas"]:
                self.centralWidget.lienzo.setAristaColor(res["aristas"], "blue")
            self.centralWidget.setNombreAlgoritmo("BFS - Anchura")

    def ejecutarDFS(self):
        inicio = self.solicitarInicio()
        if inicio is not None:
            res = AlgorithmsService.dfs(self.centralWidget.lienzo.graph, inicio)
            self.panel.setContent(res["content"])
            if res["aristas"]:
                self.centralWidget.lienzo.setAristaColor(res["aristas"], "blue")
            self.centralWidget.setNombreAlgoritmo("DFS - Profundidad")

    def ejecutarKruskal(self):
        if isinstance(self.centralWidget.lienzo.graph, nx.DiGraph):
            QMessageBox.warning(self, "Algoritmo Incompatible", "El algoritmo de Kruskal solo se puede ejecutar en Grafos No Dirigidos.")
            return

        if not self.centralWidget.lienzo.graph.edges():
            QMessageBox.warning(self, "Advertencia", "El grafo no tiene aristas para el árbol.")
            return
            
        res = AlgorithmsService.kruskal(self.centralWidget.lienzo.graph)
        self.panel.setContent(res["content"])
        if res["aristas"]:
            self.centralWidget.lienzo.setAristaColor(res["aristas"], "blue")
        self.centralWidget.setNombreAlgoritmo("Kruskal - Árbol Mínimo")

    def ejecutarDijkstra(self):
        inicio = self.solicitarInicio()
        if inicio is not None:
            res = AlgorithmsService.dijkstra(self.centralWidget.lienzo.graph, inicio)
            self.panel.setContent(res["content"])
            if res["aristas"]:
                self.centralWidget.lienzo.setAristaColor(res["aristas"], "blue")
            self.centralWidget.setNombreAlgoritmo("Dijkstra - Camino Mínimo")

    def ejecutarCentralidad(self):
        if not self.centralWidget.lienzo.graph.nodes():
            QMessageBox.warning(self, "Advertencia", "El grafo no tiene nodos para analizar.")
            return

        scores = nx.degree_centrality(self.centralWidget.lienzo.graph)
        top_nodes = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:5]

        lines = ["Centralidad de grado:"]
        for index, (node, score) in enumerate(top_nodes, start=1):
            lines.append(f"{index}. Nodo {node}: {score:.3f}")

        self.panel.setContent("\n".join(lines))
        self.centralWidget.lienzo.setAnalysisHighlights(dict(top_nodes))
        self.centralWidget.lienzo.DibujarGrafo()
        self.centralWidget.setNombreAlgoritmo("Centralidad de grado")

    def limpiarSelecciones(self):
        """Restablece el color de todas las aristas."""
        self.centralWidget.lienzo.clearAnalysisHighlights()
        if self.centralWidget.lienzo.graph.edges():
            for edge in self.centralWidget.lienzo.graph.edges():
                self.centralWidget.lienzo.edge_colors[edge] = '#2c3e50'
            self.centralWidget.lienzo.DibujarGrafo()
            self.centralWidget.setNombreAlgoritmo("")
            self.panel.setContent("Ejecuta un algoritmo para ver los pasos.")

    def buildGraphSummaryText(self):
        graph = self.centralWidget.lienzo.model.graph
        graph_type = "Grafo Dirigido" if isinstance(graph, nx.DiGraph) else "Grafo No Dirigido"

        total_nodes = graph.number_of_nodes()
        total_edges = graph.number_of_edges()
        degree_values = [degree for _, degree in graph.degree()]
        avg_degree = (sum(degree_values) / total_nodes) if total_nodes else 0

        if total_nodes == 0:
            lines = [
                "Resumen del grafo",
                "=================",
                f"Tipo: {graph_type}",
                "Nodos: 0",
                "Aristas: 0",
                "Componentes conexas: 0",
                "Nodos aislados: 0",
                f"Grado promedio: {avg_degree:.2f}",
            ]
        elif isinstance(graph, nx.DiGraph):
            weak_components = nx.number_weakly_connected_components(graph)
            strong_components = nx.number_strongly_connected_components(graph)
            isolated_nodes = sum(1 for degree in degree_values if degree == 0)
            lines = [
                "Resumen del grafo",
                "=================",
                f"Tipo: {graph_type}",
                f"Nodos: {total_nodes}",
                f"Aristas: {total_edges}",
                f"Componentes débilmente conexas: {weak_components}",
                f"Componentes fuertemente conexas: {strong_components}",
                f"Nodos aislados: {isolated_nodes}",
                f"Grado promedio: {avg_degree:.2f}",
            ]
        else:
            components = nx.number_connected_components(graph)
            isolated_nodes = sum(1 for degree in degree_values if degree == 0)
            lines = [
                "Resumen del grafo",
                "=================",
                f"Tipo: {graph_type}",
                f"Nodos: {total_nodes}",
                f"Aristas: {total_edges}",
                f"Componentes conexas: {components}",
                f"Nodos aislados: {isolated_nodes}",
                f"Grado promedio: {avg_degree:.2f}",
            ]

        if self.centralWidget.lienzo.selected_node is not None:
            selected_node = self.centralWidget.lienzo.selected_node
            position = self.centralWidget.lienzo.pos.get(selected_node)
            lines.extend([
                "",
                f"Selección actual: Nodo {selected_node}",
                f"Posición: {position if position is not None else 'Sin posición disponible'}",
            ])
        elif self.centralWidget.lienzo.selected_edge is not None:
            selected_edge = self.centralWidget.lienzo.selected_edge
            edge_data = graph.get_edge_data(*selected_edge, default={})
            weight = edge_data.get('weight', 1)
            lines.extend([
                "",
                f"Selección actual: Arista {selected_edge[0]} -> {selected_edge[1]}",
                f"Peso: {weight}",
            ])

        return "\n".join(lines)

    def guardarResumen(self):
        file_path, _ = QFileDialog.getSaveFileName(self, 'Guardar Resumen', '', 'Text Files (*.txt);;All Files (*)')
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(self.buildGraphSummaryText())
                file.write('\n')
        except OSError as exc:
            QMessageBox.warning(self, 'Error', f'No se pudo guardar el resumen: {exc}')

    def clearAnalysisState(self):
        lienzo = self.centralWidget.lienzo
        lienzo.clearAnalysisHighlights()
        lienzo.selected_node = None
        lienzo.selected_edge = None
        lienzo.selected_nodes.clear()
        lienzo.selected_edges.clear()
        lienzo.setVisualFilter('all')
        self.panel.setContent("Ejecuta un algoritmo para ver los pasos.")
        self.centralWidget.setNombreAlgoritmo("")
        self.updateSelectionInfo()
        self.updateGraphStats()
        self.centralWidget.lienzo.DibujarGrafo()

    def updateSelectionInfo(self, selected_node=None, selected_edge=None):
        graph = self.centralWidget.lienzo.model.graph
        selected_nodes = self.centralWidget.lienzo.selected_nodes if hasattr(self.centralWidget.lienzo, 'selected_nodes') else set()
        selected_edges = self.centralWidget.lienzo.selected_edges if hasattr(self.centralWidget.lienzo, 'selected_edges') else set()

        if selected_node is None and selected_edge is None and not selected_nodes and not selected_edges:
            self.panel.clearSelectionInfo()
            self.panel.btnEditarSeleccion.setEnabled(False)
            self.panel.btnEliminarSeleccion.setEnabled(False)
            return

        if selected_nodes:
            nodes_text = ", ".join(map(str, sorted(selected_nodes)))
            positions = []
            for node in sorted(selected_nodes):
                position = self.centralWidget.lienzo.pos.get(node)
                if position is not None:
                    positions.append(f"{node}: ({position[0]:.3f}, {position[1]:.3f})")
                else:
                    positions.append(f"{node}: sin posición")

            details = (
                f"Nodos seleccionados ({len(selected_nodes)}): {nodes_text}\n"
                f"Posiciones: {'; '.join(positions)}"
            )
            self.panel.setSelectionInfo(details)
            self.panel.btnEditarSeleccion.setEnabled(True)
            self.panel.btnEliminarSeleccion.setEnabled(True)
            return

        if selected_edges:
            edges_text = "; ".join(
                f"{edge[0]} -> {edge[1]}" for edge in sorted(selected_edges, key=lambda item: (item[0], item[1]))
            )
            details = f"Aristas seleccionadas ({len(selected_edges)}): {edges_text}"
            self.panel.setSelectionInfo(details)
            self.panel.btnEditarSeleccion.setEnabled(True)
            self.panel.btnEliminarSeleccion.setEnabled(True)
            return

        if selected_node is not None:
            position = self.centralWidget.lienzo.pos.get(selected_node)
            degree = graph.degree(selected_node)

            if isinstance(graph, nx.DiGraph):
                predecessors = list(graph.predecessors(selected_node))
                successors = list(graph.successors(selected_node))
                neighbors = sorted(set(predecessors) | set(successors))
                details = (
                    f"Nodo seleccionado: {selected_node}\n"
                    f"Grado total: {degree}\n"
                    f"Predecesores: {', '.join(map(str, predecessors)) if predecessors else 'Ninguno'}\n"
                    f"Sucesores: {', '.join(map(str, successors)) if successors else 'Ninguno'}\n"
                    f"Vecinos: {', '.join(map(str, neighbors)) if neighbors else 'Ninguno'}"
                )
            else:
                neighbors = sorted(graph.neighbors(selected_node))
                details = (
                    f"Nodo seleccionado: {selected_node}\n"
                    f"Grado: {degree}\n"
                    f"Vecinos: {', '.join(map(str, neighbors)) if neighbors else 'Ninguno'}"
                )

            if position is None:
                details += "\nSin posición disponible."
            else:
                details += f"\nPosición: ({position[0]:.3f}, {position[1]:.3f})"

            self.panel.setSelectionInfo(details)
            self.panel.btnEditarSeleccion.setEnabled(True)
            self.panel.btnEliminarSeleccion.setEnabled(True)
            return

        if selected_edge is not None:
            edge_data = graph.get_edge_data(*selected_edge, default={})
            weight = edge_data.get('weight', 1)
            details = (
                f"Arista seleccionada: {selected_edge[0]} -> {selected_edge[1]}\n"
                f"Peso: {weight}"
            )
            if isinstance(graph, nx.DiGraph):
                details += "\nTipo: dirigida"
            else:
                details += "\nTipo: no dirigida"

            self.panel.setSelectionInfo(details)
            self.panel.btnEditarSeleccion.setEnabled(True)
            self.panel.btnEliminarSeleccion.setEnabled(True)
            return

        self.panel.clearSelectionInfo()
        self.panel.btnEditarSeleccion.setEnabled(False)
        self.panel.btnEliminarSeleccion.setEnabled(False)

    def updateGraphStats(self):
        graph = self.centralWidget.lienzo.model.graph
        graph_type = "Grafo Dirigido" if isinstance(graph, nx.DiGraph) else "Grafo No Dirigido"
        total_nodes = graph.number_of_nodes()
        total_edges = graph.number_of_edges()
        degree_values = [degree for _, degree in graph.degree()]
        avg_degree = (sum(degree_values) / total_nodes) if total_nodes else 0

        visible_graph = self.centralWidget.lienzo._get_visible_graph()
        visible_nodes = visible_graph.number_of_nodes()
        visible_edges = visible_graph.number_of_edges()

        if self.centralWidget.lienzo.visual_filter == 'all':
            view_label = "Vista actual: Todo"
        elif self.centralWidget.lienzo.visual_filter == 'hide_isolated':
            view_label = "Vista actual: Sin aislados"
        else:
            view_label = "Vista actual: Componente actual"

        self.panel.setViewInfo(
            f"{view_label}\n"
            f"Nodos visibles: {visible_nodes}\n"
            f"Aristas visibles: {visible_edges}"
        )

        if total_nodes == 0:
            stats = (
                f"Resumen del grafo:\n"
                f"Nodos: 0\n"
                f"Aristas: 0\n"
                f"Tipo: {graph_type}\n"
                f"Componentes conexas: 0\n"
                f"Nodos aislados: 0\n"
                f"Grado promedio: 0.00"
            )
            self.panel.setStats(stats)
            return

        if isinstance(graph, nx.DiGraph):
            weak_components = nx.number_weakly_connected_components(graph)
            strong_components = nx.number_strongly_connected_components(graph)
            isolated_nodes = sum(1 for degree in degree_values if degree == 0)
            stats = (
                f"Resumen del grafo:\n"
                f"Nodos: {total_nodes}\n"
                f"Aristas: {total_edges}\n"
                f"Tipo: {graph_type}\n"
                f"Componentes débilmente conexas: {weak_components}\n"
                f"Componentes fuertemente conexas: {strong_components}\n"
                f"Nodos aislados: {isolated_nodes}\n"
                f"Grado promedio: {avg_degree:.2f}"
            )
        else:
            components = nx.number_connected_components(graph)
            isolated_nodes = sum(1 for degree in degree_values if degree == 0)
            stats = (
                f"Resumen del grafo:\n"
                f"Nodos: {total_nodes}\n"
                f"Aristas: {total_edges}\n"
                f"Tipo: {graph_type}\n"
                f"Componentes conexas: {components}\n"
                f"Nodos aislados: {isolated_nodes}\n"
                f"Grado promedio: {avg_degree:.2f}"
            )

        self.panel.setStats(stats)

    def handleSelectionEdit(self):
        if self.centralWidget.lienzo.selected_node is not None:
            self.editarNodoSeleccionado()
            return

        if self.centralWidget.lienzo.selected_edge is not None:
            self.centralWidget.editarPesoArista()

    def editarNodoSeleccionado(self):
        selected_node = self.centralWidget.lienzo.selected_node
        if selected_node is None:
            return

        position = self.centralWidget.lienzo.pos.get(selected_node, (0.0, 0.0))
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Editar nodo {selected_node}")

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"Nodo seleccionado: {selected_node}"))

        x_layout = QHBoxLayout()
        x_label = QLabel("Posición X:")
        x_edit = QLineEdit(str(position[0]))
        x_layout.addWidget(x_label)
        x_layout.addWidget(x_edit)
        layout.addLayout(x_layout)

        y_layout = QHBoxLayout()
        y_label = QLabel("Posición Y:")
        y_edit = QLineEdit(str(position[1]))
        y_layout.addWidget(y_label)
        y_layout.addWidget(y_edit)
        layout.addLayout(y_layout)

        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Guardar")
        cancel_button = QPushButton("Cancelar")

        def guardar():
            try:
                nueva_x = float(x_edit.text())
                nueva_y = float(y_edit.text())
            except ValueError:
                QMessageBox.warning(self, "Error", "Las posiciones deben ser números válidos.")
                return

            self.centralWidget.lienzo.model.set_node_position(selected_node, (nueva_x, nueva_y))
            self.centralWidget.lienzo.pos = self.centralWidget.lienzo.model.pos
            self.centralWidget.lienzo.DibujarGrafo()
            self.updateSelectionInfo(selected_node, None)
            self.updateGraphStats()
            dialog.accept()

        save_button.clicked.connect(guardar)
        cancel_button.clicked.connect(dialog.reject)
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        dialog.exec()

    def handleSelectionDelete(self):
        lienzo = self.centralWidget.lienzo
        nodes = set(lienzo.selected_nodes)
        if lienzo.selected_node is not None:
            nodes.add(lienzo.selected_node)
        edges = set(lienzo.selected_edges)
        if lienzo.selected_edge is not None:
            edges.add(lienzo.selected_edge)

        for u, v in edges:
            if lienzo.model.graph.has_edge(u, v):
                lienzo.model.eliminar_arista(u, v)
        for node in nodes:
            if node in lienzo.model.graph:
                lienzo.model.eliminar_nodo(node)

        lienzo.clearSelection()
        lienzo._refresh_after_change()


if __name__ == "__main__":
    sys.excepthook = manejarExcepcionNoCapturada
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())
