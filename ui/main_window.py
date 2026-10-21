from pathlib import Path

import networkx as nx
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QDialog, QDockWidget, QFileDialog, QMainWindow, QMessageBox

from core.algorithms import AlgorithmsService
from core.graph_stats import format_stats
from ui.dialogs import DialogoNodo, DialogoPosicion
from ui.editor_panel import PanelVista
from ui.info_panel import Panel
from ui.styles import APP_STYLESHEET

DATOS_PRUEBA = Path(__file__).resolve().parent.parent / "datos_prueba.json"
COLOR_RESULTADO = "blue"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        self.setStyleSheet(APP_STYLESHEET)

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
        self.panel.btnEditarSeleccion.clicked.connect(self.handleSelectionEdit)
        self.panel.btnEliminarSeleccion.clicked.connect(self.handleSelectionDelete)
        self.panel.btnLimpiarAnalisis.clicked.connect(self.clearAnalysisState)
        self.updateGraphStats()

    @property
    def lienzo(self):
        return self.centralWidget.lienzo

    def setupMenuBar(self):
        menubar = self.menuBar()

        # Archivo
        menuArchivo = menubar.addMenu("&Archivo")

        btnNuevo = QAction('Nuevo Grafo', self)
        btnNuevo.setShortcut(QKeySequence.StandardKey.New)
        btnNuevo.triggered.connect(self.nuevoGrafo)

        btnCargarJson = QAction('Abrir Grafo...', self)
        btnCargarJson.setShortcut(QKeySequence.StandardKey.Open)
        btnCargarJson.triggered.connect(self.abrirGrafo)

        btnGuardarJson = QAction('Guardar Grafo', self)
        btnGuardarJson.setShortcut(QKeySequence.StandardKey.Save)
        btnGuardarJson.triggered.connect(self.guardarGrafo)

        btnGuardarComo = QAction('Guardar Grafo como...', self)
        btnGuardarComo.setShortcut(QKeySequence("Ctrl+Shift+S"))
        btnGuardarComo.triggered.connect(self.guardarGrafoComo)

        btnGuardarImagen = QAction('Exportar Imagen...', self)
        btnGuardarImagen.setShortcut('Ctrl+I')
        btnGuardarImagen.triggered.connect(self.lienzo.GuardarIMG)

        btnGuardarResumen = QAction('Exportar Resumen...', self)
        btnGuardarResumen.triggered.connect(self.guardarResumen)

        btnSalir = QAction('Salir', self)
        btnSalir.setShortcut(QKeySequence("Ctrl+Q"))
        btnSalir.triggered.connect(self.close)

        menuArchivo.addAction(btnNuevo)
        menuArchivo.addAction(btnCargarJson)
        menuArchivo.addSeparator()
        menuArchivo.addAction(btnGuardarJson)
        menuArchivo.addAction(btnGuardarComo)
        menuArchivo.addSeparator()
        menuArchivo.addAction(btnGuardarImagen)
        menuArchivo.addAction(btnGuardarResumen)
        menuArchivo.addSeparator()
        menuArchivo.addAction(btnSalir)

        # Editar
        menuEditar = menubar.addMenu("&Editar")

        self.actDeshacer = QAction('Deshacer', self)
        self.actDeshacer.setShortcut(QKeySequence.StandardKey.Undo)
        self.actDeshacer.triggered.connect(self.lienzo.Deshacer)
        menuEditar.addAction(self.actDeshacer)

        self.actRehacer = QAction('Rehacer', self)
        self.actRehacer.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        self.actRehacer.triggered.connect(self.lienzo.Rehacer)
        menuEditar.addAction(self.actRehacer)

        menuEditar.addSeparator()

        actEliminarSeleccion = QAction('Eliminar selección', self)
        actEliminarSeleccion.setShortcut(QKeySequence.StandardKey.Delete)
        actEliminarSeleccion.triggered.connect(self.handleSelectionDelete)
        menuEditar.addAction(actEliminarSeleccion)

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

    # ── Archivo ────────────────────────────────────────────────

    def nuevoGrafo(self):
        if self.confirmarCambiosPendientes():
            self.lienzo.nuevoGrafo()

    def abrirGrafo(self):
        if not self.confirmarCambiosPendientes():
            return
        ruta, _ = QFileDialog.getOpenFileName(self, 'Abrir Grafo', '', 'JSON Files (*.json);;All Files (*)')
        if ruta:
            self.lienzo.cargarJson(ruta)

    def dibujaPruebaGrafo(self):
        if not self.confirmarCambiosPendientes():
            return
        if self.lienzo.cargarJson(str(DATOS_PRUEBA), como_plantilla=True):
            self.centralWidget.setNombreAlgoritmo("Grafo de Prueba")

    def guardarGrafo(self):
        """Guarda en el archivo actual; si no hay, pide uno. Devuelve True si se guardó."""
        if self.lienzo.ruta_actual is None:
            return self.guardarGrafoComo()
        return self._guardarEn(self.lienzo.ruta_actual)

    def guardarGrafoComo(self):
        sugerido = self.lienzo.ruta_actual or f"{self.lienzo.nombre_documento}.json"
        ruta, _ = QFileDialog.getSaveFileName(self, 'Guardar Grafo como', sugerido, 'JSON Files (*.json);;All Files (*)')
        if not ruta:
            return False
        if not Path(ruta).suffix:
            ruta += ".json"
        return self._guardarEn(ruta)

    def _guardarEn(self, ruta):
        try:
            self.lienzo.guardarEnJSON(ruta)
        except OSError as exc:
            QMessageBox.warning(self, "Error al guardar", f"No se pudo guardar el grafo:\n{exc}")
            return False
        return True

    def confirmarCambiosPendientes(self):
        """Si hay cambios sin guardar, pregunta qué hacer. Devuelve True si se puede continuar."""
        if not self.lienzo.hay_cambios:
            return True

        respuesta = QMessageBox.question(
            self,
            "Cambios sin guardar",
            f"El grafo \"{self.lienzo.nombre_documento}\" tiene cambios sin guardar.\n¿Deseas guardarlos?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if respuesta == QMessageBox.StandardButton.Save:
            return self.guardarGrafo()
        return respuesta == QMessageBox.StandardButton.Discard

    def closeEvent(self, event):
        if self.confirmarCambiosPendientes():
            event.accept()
        else:
            event.ignore()

    def _actualizarTitulo(self):
        self.setWindowTitle(f"{self.lienzo.nombre_documento}[*] - VISUALIZADOR DE GRAFOS - ADA")
        self.setWindowModified(self.lienzo.hay_cambios)

    # ── Algoritmos ──────────────────────────────────────────────

    def solicitarInicio(self):
        if not self.lienzo.graph.nodes():
            QMessageBox.warning(self, "Advertencia", "El grafo no tiene nodos.")
            return None

        dialogN = DialogoNodo("Inicio de Recorrido", "Ingresa el ID del Nodo de inicio:", self)
        if dialogN.exec() == QDialog.DialogCode.Accepted:
            try:
                return int(dialogN.valor1)
            except ValueError:
                QMessageBox.warning(self, "Error", "El ID debe ser un número entero.")
        return None

    def mostrarResultado(self, res, nombre):
        self.panel.setContent(res["content"])
        if res["aristas"]:
            self.lienzo.setAristaColor(res["aristas"], COLOR_RESULTADO)
        self.centralWidget.setNombreAlgoritmo(nombre)

    def ejecutarBFS(self):
        inicio = self.solicitarInicio()
        if inicio is not None:
            self.mostrarResultado(AlgorithmsService.bfs(self.lienzo.graph, inicio), "BFS - Anchura")

    def ejecutarDFS(self):
        inicio = self.solicitarInicio()
        if inicio is not None:
            self.mostrarResultado(AlgorithmsService.dfs(self.lienzo.graph, inicio), "DFS - Profundidad")

    def ejecutarKruskal(self):
        if self.lienzo.graph.is_directed():
            QMessageBox.warning(self, "Algoritmo Incompatible", "El algoritmo de Kruskal solo se puede ejecutar en Grafos No Dirigidos.")
            return

        if not self.lienzo.graph.edges():
            QMessageBox.warning(self, "Advertencia", "El grafo no tiene aristas para el árbol.")
            return

        self.mostrarResultado(AlgorithmsService.kruskal(self.lienzo.graph), "Kruskal - Árbol Mínimo")

    def ejecutarDijkstra(self):
        inicio = self.solicitarInicio()
        if inicio is not None:
            self.mostrarResultado(AlgorithmsService.dijkstra(self.lienzo.graph, inicio), "Dijkstra - Camino Mínimo")

    def ejecutarCentralidad(self):
        if not self.lienzo.graph.nodes():
            QMessageBox.warning(self, "Advertencia", "El grafo no tiene nodos para analizar.")
            return

        scores = nx.degree_centrality(self.lienzo.graph)
        top_nodes = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:5]

        lines = ["Centralidad de grado:"]
        for index, (node, score) in enumerate(top_nodes, start=1):
            lines.append(f"{index}. Nodo {node}: {score:.3f}")

        self.panel.setContent("\n".join(lines))
        self.lienzo.setAnalysisHighlights(dict(top_nodes))
        self.lienzo.DibujarGrafo()
        self.centralWidget.setNombreAlgoritmo("Centralidad de grado")

    def limpiarSelecciones(self):
        """Restablece el color de todas las aristas."""
        self.lienzo.clearAnalysisHighlights()
        if self.lienzo.graph.edges():
            self.lienzo.setAristaColor([], COLOR_RESULTADO)
            self.centralWidget.setNombreAlgoritmo("")
            self.panel.clearContent()

    # ── Resumen y estadísticas ─────────────────────────────────

    def buildGraphSummaryText(self):
        graph = self.lienzo.graph
        lines = ["Resumen del grafo", "================="] + format_stats(graph)

        if self.lienzo.selected_node is not None:
            selected_node = self.lienzo.selected_node
            position = self.lienzo.pos.get(selected_node)
            lines.extend([
                "",
                f"Selección actual: Nodo {selected_node}",
                f"Posición: {position if position is not None else 'Sin posición disponible'}",
            ])
        elif self.lienzo.selected_edge is not None:
            selected_edge = self.lienzo.selected_edge
            weight = graph.get_edge_data(*selected_edge, default={}).get('weight', 1)
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
        lienzo = self.lienzo
        lienzo.clearAnalysisHighlights()
        lienzo.clearSelection()
        lienzo.setVisualFilter('all')
        self.panel.clearContent()
        self.centralWidget.setNombreAlgoritmo("")
        self.updateSelectionInfo()
        self.updateGraphStats()
        lienzo.DibujarGrafo()

    def updateGraphStats(self):
        lienzo = self.lienzo
        visible_graph = lienzo._get_visible_graph()

        view_labels = {
            'all': "Vista actual: Todo",
            'hide_isolated': "Vista actual: Sin aislados",
            'component': "Vista actual: Componente actual",
        }
        self.panel.setViewInfo(
            f"{view_labels.get(lienzo.visual_filter, view_labels['all'])}\n"
            f"Nodos visibles: {visible_graph.number_of_nodes()}\n"
            f"Aristas visibles: {visible_graph.number_of_edges()}"
        )
        self.panel.setStats("\n".join(["Resumen del grafo:"] + format_stats(lienzo.graph)))
        self.actDeshacer.setEnabled(lienzo.history.can_undo)
        self.actRehacer.setEnabled(lienzo.history.can_redo)
        self._actualizarTitulo()

    def clearAlgorithmResult(self):
        self.panel.clearContent()
        self.centralWidget.setNombreAlgoritmo("")

    # ── Selección ──────────────────────────────────────────────

    def _set_selection_buttons(self, enabled):
        self.panel.btnEditarSeleccion.setEnabled(enabled)
        self.panel.btnEliminarSeleccion.setEnabled(enabled)

    def updateSelectionInfo(self, selected_node=None, selected_edge=None):
        lienzo = self.lienzo
        graph = lienzo.graph
        selected_nodes = lienzo.selected_nodes
        selected_edges = lienzo.selected_edges

        if selected_nodes:
            positions = []
            for node in sorted(selected_nodes):
                position = lienzo.pos.get(node)
                if position is not None:
                    positions.append(f"{node}: ({position[0]:.3f}, {position[1]:.3f})")
                else:
                    positions.append(f"{node}: sin posición")

            nodes_text = ", ".join(map(str, sorted(selected_nodes)))
            self.panel.setSelectionInfo(
                f"Nodos seleccionados ({len(selected_nodes)}): {nodes_text}\n"
                f"Posiciones: {'; '.join(positions)}"
            )
            self._set_selection_buttons(True)
            return

        if selected_edges:
            edges_text = "; ".join(f"{u} -> {v}" for u, v in sorted(selected_edges))
            self.panel.setSelectionInfo(f"Aristas seleccionadas ({len(selected_edges)}): {edges_text}")
            self._set_selection_buttons(True)
            return

        if selected_node is not None:
            position = lienzo.pos.get(selected_node)
            degree = graph.degree(selected_node)

            if graph.is_directed():
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
            self._set_selection_buttons(True)
            return

        if selected_edge is not None:
            weight = graph.get_edge_data(*selected_edge, default={}).get('weight', 1)
            tipo = "dirigida" if graph.is_directed() else "no dirigida"
            self.panel.setSelectionInfo(
                f"Arista seleccionada: {selected_edge[0]} -> {selected_edge[1]}\n"
                f"Peso: {weight}\n"
                f"Tipo: {tipo}"
            )
            self._set_selection_buttons(True)
            return

        self.panel.clearSelectionInfo()
        self._set_selection_buttons(False)

    def handleSelectionEdit(self):
        if self.lienzo.selected_node is not None:
            self.editarNodoSeleccionado()
            return

        if self.lienzo.selected_edge is not None:
            self.centralWidget.editarPesoArista()

    def editarNodoSeleccionado(self):
        selected_node = self.lienzo.selected_node
        if selected_node is None:
            return

        position = self.lienzo.pos.get(selected_node, (0.0, 0.0))
        dialog = DialogoPosicion(selected_node, position, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.lienzo.moverNodo(selected_node, dialog.posicion)

    def handleSelectionDelete(self):
        self.lienzo.eliminarSeleccion()
