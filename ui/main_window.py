from pathlib import Path

import networkx as nx
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QActionGroup, QCursor, QKeySequence
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDockWidget, QFileDialog, QFrame, QInputDialog, QLabel,
    QMainWindow, QMenu, QMessageBox, QToolBar, QVBoxLayout,
)

from core.algorithms import AlgorithmsService
from core.graph_stats import format_stats
from ui.canvas import MODO_ARISTA, MODO_NODO, MODO_SELECCIONAR, Lienzo
from ui.dialogs import DialogoArista, DialogoNodo, DialogoPosicion
from ui import theme
from ui.info_panel import Panel
from ui.styles import APP_STYLESHEET

DATOS_PRUEBA = Path(__file__).resolve().parent.parent / "datos_prueba.json"
COLOR_RESULTADO = theme.RESULTADO
PESO_MAXIMO = 1_000_000

TIPOS_GRAFO = [("Undirected", "No dirigido"), ("Directed", "Dirigido")]

AYUDA_MODOS = {
    MODO_SELECCIONAR: "Seleccionar: clic para seleccionar, arrastra nodos para moverlos o el fondo para desplazar la vista.",
    MODO_NODO: "Nodo: clic en un espacio vacío para crear un nodo.",
    MODO_ARISTA: "Arista: clic en el nodo origen y luego en el nodo destino.",
}

TEXTO_AYUDA = """
<h3>Modos de edición</h3>
<ul>
<li><b>V</b> Seleccionar: clic para seleccionar; Ctrl/Shift + clic para selección múltiple;
arrastra un nodo para moverlo o el fondo para desplazar la vista.</li>
<li><b>N</b> Nodo: clic en un espacio vacío para crear un nodo.</li>
<li><b>E</b> Arista: clic en el nodo origen y luego en el destino; se pide el peso.</li>
</ul>
<h3>Acciones rápidas</h3>
<ul>
<li><b>Clic derecho</b> sobre un nodo, una arista o el fondo: menú con las acciones disponibles
(por ejemplo, ejecutar un algoritmo desde ese nodo).</li>
<li><b>Doble clic</b> sobre una arista: editar su peso.</li>
<li><b>Supr</b> / <b>Retroceso</b>: eliminar la selección. <b>Esc</b>: cancelar.</li>
<li><b>Ctrl+Z</b> / <b>Ctrl+Y</b>: deshacer / rehacer.</li>
<li><b>Rueda</b>: zoom. <b>Botón central</b> o arrastrar el fondo: desplazar.
<b>F</b>: ajustar la vista al grafo.</li>
</ul>
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        self.setStyleSheet(APP_STYLESHEET)

        self.lienzo = Lienzo(self)
        contenedor = QFrame()
        contenedor.setObjectName("contenedorLienzo")
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.lienzo.canvas)
        self.setCentralWidget(contenedor)

        self.dock_widget = QDockWidget("Panel de Información", self)
        self.dock_widget.setObjectName("panelInformacion")
        self.panel = Panel()
        self.panel.setMinimumWidth(300)
        self.dock_widget.setWidget(self.panel)
        self.dock_widget.setMaximumWidth(380)
        self.dock_widget.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_widget)

        self.setupActions()
        self.setupMenuBar()
        self.setupToolBar()
        self.setupStatusBar()
        self.conectarLienzo()

        self.panel.btnEditarSeleccion.clicked.connect(self.handleSelectionEdit)
        self.panel.btnEliminarSeleccion.clicked.connect(self.handleSelectionDelete)
        self.panel.btnLimpiarAnalisis.clicked.connect(self.clearAnalysisState)

        self.setModo(MODO_SELECCIONAR)
        self.updateGraphStats()
        self.updateSelectionInfo()

    # ── Construcción de la interfaz ────────────────────────────

    def _accion(self, texto, slot, atajo=None, tooltip=None, checkable=False):
        accion = QAction(texto, self)
        if atajo is not None:
            atajos = atajo if isinstance(atajo, list) else [atajo]
            accion.setShortcuts([QKeySequence(a) for a in atajos])
        if tooltip:
            atajo_texto = accion.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
            accion.setToolTip(f"{tooltip} ({atajo_texto})" if atajo_texto else tooltip)
            accion.setStatusTip(tooltip)
        accion.setCheckable(checkable)
        if slot is not None:
            accion.triggered.connect(lambda _checked=False: slot())
        return accion

    def setupActions(self):
        self.grupoModos = QActionGroup(self)
        self.grupoModos.setExclusive(True)
        self.actModos = {}
        for modo, texto, atajo, ayuda in [
            (MODO_SELECCIONAR, "↖  Seleccionar", "V", "Seleccionar y mover"),
            (MODO_NODO, "●  Nodo", "N", "Agregar nodos con un clic"),
            (MODO_ARISTA, "╱  Arista", "E", "Agregar aristas: clic en origen y destino"),
        ]:
            accion = self._accion(texto, lambda m=modo: self.setModo(m), atajo, ayuda, checkable=True)
            self.grupoModos.addAction(accion)
            self.actModos[modo] = accion

        self.actDeshacer = self._accion("↶  Deshacer", self.lienzo.Deshacer, QKeySequence.StandardKey.Undo, "Deshacer")
        self.actRehacer = self._accion("↷  Rehacer", self.lienzo.Rehacer, ["Ctrl+Y", "Ctrl+Shift+Z"], "Rehacer")
        self.actEliminar = self._accion(
            "✕  Eliminar", self.handleSelectionDelete,
            [QKeySequence.StandardKey.Delete, "Backspace"], "Eliminar la selección",
        )
        self.actEditar = self._accion("✎  Editar", self.handleSelectionEdit, "F2", "Editar el nodo o la arista seleccionada")
        self.actCancelar = self._accion("Cancelar", self.lienzo.cancelarAccion, "Esc", "Cancelar la acción en curso")
        self.actAjustarVista = self._accion("⤢  Ajustar vista", self.lienzo.ajustarVista, "F", "Encuadrar todo el grafo")

        self.grupoFiltros = QActionGroup(self)
        self.actFiltros = {}
        for filtro, texto in [
            ('all', "Mostrar todo"),
            ('hide_isolated', "Ocultar nodos aislados"),
            ('component', "Solo la componente del nodo seleccionado"),
        ]:
            accion = self._accion(texto, lambda f=filtro: self.aplicarFiltro(f), checkable=True)
            self.grupoFiltros.addAction(accion)
            self.actFiltros[filtro] = accion
        self.actFiltros['all'].setChecked(True)

    def setupMenuBar(self):
        menubar = self.menuBar()

        menuArchivo = menubar.addMenu("&Archivo")
        menuArchivo.addAction(self._accion('Nuevo Grafo', self.nuevoGrafo, QKeySequence.StandardKey.New))
        menuArchivo.addAction(self._accion('Abrir Grafo...', self.abrirGrafo, QKeySequence.StandardKey.Open))
        menuArchivo.addSeparator()
        menuArchivo.addAction(self._accion('Guardar Grafo', self.guardarGrafo, QKeySequence.StandardKey.Save))
        menuArchivo.addAction(self._accion('Guardar Grafo como...', self.guardarGrafoComo, "Ctrl+Shift+S"))
        menuArchivo.addSeparator()
        menuArchivo.addAction(self._accion('Exportar Imagen...', self.exportarImagen, "Ctrl+I"))
        menuArchivo.addAction(self._accion('Exportar Resumen...', self.guardarResumen))
        menuArchivo.addSeparator()
        menuArchivo.addAction(self._accion('Salir', self.close, "Ctrl+Q"))

        menuEditar = menubar.addMenu("&Editar")
        menuEditar.addAction(self.actDeshacer)
        menuEditar.addAction(self.actRehacer)
        menuEditar.addSeparator()
        for accion in self.actModos.values():
            menuEditar.addAction(accion)
        menuEditar.addSeparator()
        menuEditar.addAction(self.actEditar)
        menuEditar.addAction(self.actEliminar)
        menuEditar.addAction(self.actCancelar)
        menuEditar.addSeparator()
        menuEditar.addAction(self._accion('Agregar arista por IDs...', self.agregarAristaPorIds))
        menuEditar.addAction(self._accion('Eliminar nodo por ID...', self.eliminarNodoPorId))
        menuEditar.addAction(self._accion('Eliminar arista por IDs...', self.eliminarAristaPorIds))

        menuVer = menubar.addMenu("&Ver")
        accionPanel = self.dock_widget.toggleViewAction()
        accionPanel.setText("Panel de información")
        accionPanel.setShortcut(QKeySequence("Ctrl+P"))
        menuVer.addAction(accionPanel)
        menuVer.addSeparator()
        menuVer.addAction(self._accion('Acercar', self.lienzo.zoomIn, [QKeySequence.StandardKey.ZoomIn, "Ctrl+="]))
        menuVer.addAction(self._accion('Alejar', self.lienzo.zoomOut, QKeySequence.StandardKey.ZoomOut))
        menuVer.addAction(self.actAjustarVista)
        menuVer.addAction(self._accion('Restaurar vista', self.lienzo.resetView, "Ctrl+0"))
        menuVer.addSeparator()
        for accion in self.actFiltros.values():
            menuVer.addAction(accion)

        menuGrafos = menubar.addMenu("&Grafos")
        menuGrafos.addAction(self._accion('Cargar Grafo de Prueba', self.dibujaPruebaGrafo))
        menuGrafos.addSeparator()
        menuGrafos.addAction(self._accion('Limpiar resultado del algoritmo', self.limpiarSelecciones))
        menuGrafos.addAction(self._accion('Limpiar lienzo', self.lienzo.Limpiar))

        menuAlgoritmos = menubar.addMenu("&Algoritmos")
        grupos = [
            ("Recorridos", [
                ('BFS - Búsqueda en anchura', self.ejecutarBFS),
                ('DFS - Búsqueda en profundidad', self.ejecutarDFS),
            ]),
            ("Caminos mínimos", [
                ('Dijkstra - Camino más corto', self.ejecutarDijkstra),
                ('Bellman-Ford - Admite pesos negativos', self.ejecutarBellmanFord),
            ]),
            ("Árbol de expansión mínima", [
                ('Kruskal', self.ejecutarKruskal),
                ('Prim', self.ejecutarPrim),
            ]),
            ("Análisis", [
                ('Orden topológico', self.ejecutarOrdenTopologico),
                ('Detectar ciclos', self.ejecutarDeteccionCiclos),
                ('Componentes fuertemente conexas', self.ejecutarComponentesFuertes),
                ('Centralidad de grado', self.ejecutarCentralidad),
            ]),
        ]
        for titulo, acciones in grupos:
            submenu = menuAlgoritmos.addMenu(titulo)
            for texto, slot in acciones:
                submenu.addAction(self._accion(texto, slot))

        menuAyuda = menubar.addMenu("A&yuda")
        menuAyuda.addAction(self._accion('Atajos y uso...', self.mostrarAyuda, QKeySequence.StandardKey.HelpContents))

    def setupToolBar(self):
        barra = QToolBar("Herramientas", self)
        barra.setObjectName("barraHerramientas")
        barra.setMovable(False)
        barra.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, barra)

        for accion in self.actModos.values():
            barra.addAction(accion)
        barra.addSeparator()
        barra.addAction(self.actDeshacer)
        barra.addAction(self.actRehacer)
        barra.addSeparator()
        barra.addAction(self.actEditar)
        barra.addAction(self.actEliminar)
        barra.addSeparator()

        barra.addWidget(QLabel("  Tipo: "))
        self.comboTipo = QComboBox()
        for _, etiqueta in TIPOS_GRAFO:
            self.comboTipo.addItem(etiqueta)
        self.comboTipo.setToolTip("Tipo de grafo")
        self.comboTipo.currentIndexChanged.connect(self.onTipoGrafoSeleccionado)
        barra.addWidget(self.comboTipo)
        barra.addSeparator()
        barra.addAction(self.actAjustarVista)
        self.barraHerramientas = barra

    def setupStatusBar(self):
        barra = self.statusBar()
        self.lblModo = QLabel()
        self.lblCoordenadas = QLabel()
        self.lblCoordenadas.setMinimumWidth(130)
        barra.addPermanentWidget(self.lblModo)
        barra.addPermanentWidget(self.lblCoordenadas)

    def conectarLienzo(self):
        lienzo = self.lienzo
        lienzo.grafoCambiado.connect(self.updateGraphStats)
        lienzo.seleccionCambiada.connect(self.updateSelectionInfo)
        lienzo.resultadoDescartado.connect(self.clearAlgorithmResult)
        lienzo.tipoGrafoCambiado.connect(self.syncTipoGrafo)
        lienzo.mensaje.connect(lambda texto: self.statusBar().showMessage(texto, 5000))
        lienzo.menuContextualSolicitado.connect(self.mostrarMenuContextual)
        lienzo.aristaSolicitada.connect(self.crearAristaInteractiva)
        lienzo.edicionPesoSolicitada.connect(self.editarPesoArista)
        lienzo.cursorMovido.connect(lambda x, y: self.lblCoordenadas.setText(f"x: {x:.3f}   y: {y:.3f}"))

    # ── Modos y tipo de grafo ──────────────────────────────────

    def setModo(self, modo):
        self.actModos[modo].setChecked(True)
        self.lienzo.setModo(modo)
        self.lblModo.setText(f"Modo: {self.actModos[modo].text().split()[-1]}")
        self.statusBar().showMessage(AYUDA_MODOS[modo], 5000)

    def syncTipoGrafo(self, tipo):
        """Refleja el tipo de grafo en el selector sin disparar un cambio."""
        indice = [clave for clave, _ in TIPOS_GRAFO].index(tipo)
        self.comboTipo.blockSignals(True)
        self.comboTipo.setCurrentIndex(indice)
        self.comboTipo.blockSignals(False)

    def onTipoGrafoSeleccionado(self, indice):
        tipo = TIPOS_GRAFO[indice][0]
        if tipo == self.lienzo.model.graph_type:
            return

        if self.lienzo.graph.number_of_nodes() == 0:
            self.lienzo.cambiarTipoGrafo(tipo)
            return

        decision = self._preguntarCambioTipo(tipo)
        if decision is None:
            self.syncTipoGrafo(self.lienzo.model.graph_type)
            return
        self.lienzo.cambiarTipoGrafo(tipo, conservar=(decision == 'convertir'))

    def _preguntarCambioTipo(self, tipo):
        """Devuelve 'convertir', 'vaciar' o None (cancelar)."""
        if tipo == "Directed":
            detalle = "Cada arista pasará a ser dirigida en el sentido en que fue creada."
        else:
            detalle = "Las aristas pasarán a ser no dirigidas; si había dos opuestas, se fusionan en una."

        caja = QMessageBox(self)
        caja.setIcon(QMessageBox.Icon.Question)
        caja.setWindowTitle("Cambiar tipo de grafo")
        caja.setText(f"¿Cómo quieres pasar a un grafo {TIPOS_GRAFO[[c for c, _ in TIPOS_GRAFO].index(tipo)][1].lower()}?")
        caja.setInformativeText(f"{detalle}\nCualquier opción se puede deshacer con Ctrl+Z.")
        convertir = caja.addButton("Convertir el grafo actual", QMessageBox.ButtonRole.AcceptRole)
        vaciar = caja.addButton("Empezar uno vacío", QMessageBox.ButtonRole.DestructiveRole)
        caja.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        caja.exec()

        if caja.clickedButton() == convertir:
            return 'convertir'
        if caja.clickedButton() == vaciar:
            return 'vaciar'
        return None

    def aplicarFiltro(self, filtro):
        if filtro == 'component':
            if self.lienzo.selected_node is None:
                self.lienzo.Alertas("Primero selecciona un nodo para enfocar su componente.", titulo="Sin selección")
                self.actFiltros[self.lienzo.visual_filter].setChecked(True)
                return
            self.lienzo.focusCurrentComponent()
        else:
            self.lienzo.setVisualFilter(filtro)
        self.actFiltros[self.lienzo.visual_filter].setChecked(True)

    # ── Edición asistida por diálogos ──────────────────────────

    def _pedirPeso(self, titulo, etiqueta, valor):
        """Devuelve el peso ingresado o None si se cancela."""
        peso, ok = QInputDialog.getInt(self, titulo, etiqueta, value=valor, min=-PESO_MAXIMO, max=PESO_MAXIMO)
        return peso if ok else None

    def crearAristaInteractiva(self, origen, destino):
        peso_actual = 1
        if self.lienzo.graph.has_edge(origen, destino):
            peso_actual = self.lienzo.graph.edges[origen, destino].get('weight', 1)
        peso = self._pedirPeso("Nueva arista", f"Peso de la arista {origen} - {destino}:", peso_actual)
        if peso is not None:
            self.lienzo.DibujarArista(origen, destino, peso)

    def editarPesoArista(self, u, v):
        peso_actual = self.lienzo.graph.edges[u, v].get('weight', 1)
        peso = self._pedirPeso("Editar peso", f"Peso de la arista {u} - {v}:", peso_actual)
        if peso is not None:
            self.lienzo.actualizarPesoArista(u, v, peso)

    def agregarAristaPorIds(self):
        dialogo = DialogoArista(self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            try:
                origen, destino, peso = int(dialogo.valor1), int(dialogo.valor2), int(dialogo.valor3)
            except ValueError:
                self.lienzo.Alertas("Ingresa números enteros válidos.", titulo="Datos no válidos")
                return
            self.lienzo.DibujarArista(origen, destino, peso)

    def eliminarNodoPorId(self):
        aceptado, nodo = self._pedirNodo("Eliminar Nodo", "Ingresa el ID del Nodo a eliminar:")
        if aceptado and nodo is not None:
            self.lienzo.eliminarNodo(nodo)

    def eliminarAristaPorIds(self):
        aceptado, origen = self._pedirNodo("Eliminar Arista", "Ingresa el nodo origen:")
        if not aceptado or origen is None:
            return
        aceptado, destino = self._pedirNodo("Eliminar Arista", "Ingresa el nodo destino:")
        if aceptado and destino is not None:
            self.lienzo.eliminarArista(origen, destino)

    # ── Menú contextual ────────────────────────────────────────

    def mostrarMenuContextual(self, objetivo):
        menu = self.construirMenuContextual(objetivo)
        self._ejecutarMenu(menu)

    def _ejecutarMenu(self, menu):
        menu.exec(QCursor.pos())

    def construirMenuContextual(self, objetivo):
        menu = QMenu(self)
        lienzo = self.lienzo

        if objetivo.tipo == 'nodo':
            nodo = objetivo.valor
            menu.addSection(f"Nodo {nodo}")
            submenu = menu.addMenu(f"Ejecutar desde el nodo {nodo}")
            for texto, metodo in [
                ("BFS - Anchura", self.ejecutarBFS),
                ("DFS - Profundidad", self.ejecutarDFS),
                ("Dijkstra - Camino mínimo", self.ejecutarDijkstra),
                ("Bellman-Ford", self.ejecutarBellmanFord),
                ("Prim - Árbol mínimo", self.ejecutarPrim),
            ]:
                submenu.addAction(self._accion(texto, lambda m=metodo: m(inicio=nodo)))
            menu.addAction(self._accion("Enfocar su componente", lambda: self.aplicarFiltro('component')))
            menu.addAction(self._accion("Editar posición...", self.editarNodoSeleccionado))
            menu.addSeparator()
            menu.addAction(self._accion("Eliminar nodo", lambda: lienzo.eliminarNodo(nodo)))
        elif objetivo.tipo == 'arista':
            u, v = objetivo.valor
            menu.addSection(f"Arista {u} - {v}")
            menu.addAction(self._accion("Editar peso...", lambda: self.editarPesoArista(u, v)))
            menu.addSeparator()
            menu.addAction(self._accion("Eliminar arista", lambda: lienzo.eliminarArista(u, v)))
        else:
            menu.addAction(self._accion("Agregar nodo aquí", lambda: lienzo.agregarNodo(objetivo.x, objetivo.y)))
            menu.addSeparator()
            menu.addAction(self._accion("Ajustar vista", lienzo.ajustarVista))
            menu.addAction(self._accion("Restaurar vista", lienzo.resetView))

        return menu

    # ── Archivo ────────────────────────────────────────────────

    def nuevoGrafo(self):
        if self.confirmarCambiosPendientes():
            self.lienzo.nuevoGrafo()
            self.actFiltros['all'].setChecked(True)

    def abrirGrafo(self):
        if not self.confirmarCambiosPendientes():
            return
        ruta, _ = QFileDialog.getOpenFileName(self, 'Abrir Grafo', '', 'JSON Files (*.json);;All Files (*)')
        if ruta:
            self.lienzo.cargarJson(ruta)

    def dibujaPruebaGrafo(self):
        if not self.confirmarCambiosPendientes():
            return
        self.lienzo.cargarJson(str(DATOS_PRUEBA), como_plantilla=True)

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

    def exportarImagen(self):
        ruta, _ = QFileDialog.getSaveFileName(self, 'Exportar Imagen', '', 'PNG Files (*.png);;All Files (*)')
        if not ruta:
            return
        try:
            self.lienzo.exportarImagen(ruta, self.buildGraphSummaryText())
        except OSError as exc:
            QMessageBox.warning(self, "Error al exportar", f"No se pudo guardar la imagen:\n{exc}")
            return
        self.statusBar().showMessage(f"Imagen exportada a {ruta}", 5000)

    def guardarResumen(self):
        file_path, _ = QFileDialog.getSaveFileName(self, 'Exportar Resumen', '', 'Text Files (*.txt);;All Files (*)')
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(self.buildGraphSummaryText())
                file.write('\n')
        except OSError as exc:
            QMessageBox.warning(self, 'Error', f'No se pudo guardar el resumen: {exc}')

    def mostrarAyuda(self):
        QMessageBox.information(self, "Atajos y uso", TEXTO_AYUDA)

    # ── Algoritmos ──────────────────────────────────────────────

    def _grafoTieneNodos(self):
        if self.lienzo.graph.number_of_nodes() == 0:
            QMessageBox.warning(self, "Advertencia", "El grafo no tiene nodos.")
            return False
        return True

    def _pedirNodo(self, titulo, mensaje, sugerido=None, opcional=False):
        """Devuelve (aceptado, nodo). Con 'opcional', un campo vacío da nodo None."""
        dialogo = DialogoNodo(titulo, mensaje, self, valor_inicial=sugerido, opcional=opcional)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return False, None
        if not dialogo.valor1:
            return True, None
        try:
            return True, int(dialogo.valor1)
        except ValueError:
            QMessageBox.warning(self, "Error", "El ID debe ser un número entero.")
            return False, None

    def solicitarInicio(self):
        """Pide el nodo de inicio; propone el nodo seleccionado si lo hay."""
        if not self._grafoTieneNodos():
            return None
        _, inicio = self._pedirNodo(
            "Nodo de inicio", "Ingresa el ID del Nodo de inicio:", sugerido=self.lienzo.selected_node
        )
        return inicio

    def solicitarDestino(self):
        """Devuelve (aceptado, destino); destino None significa 'todos los nodos'."""
        return self._pedirNodo(
            "Nodo destino",
            "Ingresa el ID del Nodo destino\n(déjalo vacío para ver todos):",
            opcional=True,
        )

    def _ejecutar(self, nombre, calcular):
        try:
            resultado = calcular()
        except ValueError as exc:
            QMessageBox.warning(self, nombre, str(exc))
            return
        self.mostrarResultado(resultado, nombre)

    def mostrarResultado(self, res, nombre):
        self.lienzo.clearAnalysisHighlights()
        self.lienzo.setAristaColor(res["aristas"], COLOR_RESULTADO)
        self.panel.setResultado(nombre, res["content"])
        self.statusBar().showMessage(f"{nombre}: listo.", 5000)

    def _ejecutarDesdeInicio(self, nombre, algoritmo, inicio=None):
        if inicio is None:
            inicio = self.solicitarInicio()
        if inicio is not None:
            self._ejecutar(nombre, lambda: algoritmo(self.lienzo.graph, inicio))

    def ejecutarBFS(self, inicio=None):
        self._ejecutarDesdeInicio("BFS - Anchura", AlgorithmsService.bfs, inicio)

    def ejecutarDFS(self, inicio=None):
        self._ejecutarDesdeInicio("DFS - Profundidad", AlgorithmsService.dfs, inicio)

    def ejecutarDijkstra(self, inicio=None):
        if inicio is None:
            inicio = self.solicitarInicio()
        if inicio is None:
            return
        aceptado, destino = self.solicitarDestino()
        if aceptado:
            self._ejecutar(
                "Dijkstra - Camino Mínimo",
                lambda: AlgorithmsService.dijkstra(self.lienzo.graph, inicio, destino),
            )

    def ejecutarBellmanFord(self, inicio=None):
        self._ejecutarDesdeInicio("Bellman-Ford", AlgorithmsService.bellman_ford, inicio)

    def ejecutarKruskal(self):
        self._ejecutar("Kruskal - Árbol Mínimo", lambda: AlgorithmsService.kruskal(self.lienzo.graph))

    def ejecutarPrim(self, inicio=None):
        self._ejecutarDesdeInicio("Prim - Árbol Mínimo", AlgorithmsService.prim, inicio)

    def ejecutarOrdenTopologico(self):
        self._ejecutar("Orden Topológico", lambda: AlgorithmsService.orden_topologico(self.lienzo.graph))

    def ejecutarDeteccionCiclos(self):
        self._ejecutar("Detección de ciclos", lambda: AlgorithmsService.detectar_ciclo(self.lienzo.graph))

    def ejecutarComponentesFuertes(self):
        self._ejecutar(
            "Componentes fuertemente conexas",
            lambda: AlgorithmsService.componentes_fuertes(self.lienzo.graph),
        )

    def ejecutarCentralidad(self):
        if not self._grafoTieneNodos():
            return

        scores = nx.degree_centrality(self.lienzo.graph)
        top_nodes = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:5]

        lines = ["Centralidad de grado:"]
        for index, (node, score) in enumerate(top_nodes, start=1):
            lines.append(f"{index}. Nodo {node}: {score:.3f}")

        lines.append("")
        lines.append("El tamaño de cada nodo es proporcional a su centralidad.")

        self.lienzo.setAnalysisHighlights(scores)
        self.lienzo.setAristaColor([], COLOR_RESULTADO)
        self.panel.setResultado("Centralidad de grado", "\n".join(lines))

    def limpiarSelecciones(self):
        """Quita el resultado del algoritmo del lienzo y del panel."""
        self.lienzo.clearAnalysisHighlights()
        self.lienzo.setAristaColor([], COLOR_RESULTADO)
        self.clearAlgorithmResult()

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

    def clearAnalysisState(self):
        lienzo = self.lienzo
        lienzo.clearAnalysisHighlights()
        lienzo.clearSelection()
        lienzo.setAristaColor([], COLOR_RESULTADO)
        self.aplicarFiltro('all')
        self.clearAlgorithmResult()
        self.updateSelectionInfo()

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
        self.actFiltros[lienzo.visual_filter].setChecked(True)
        self._actualizarTitulo()

    def clearAlgorithmResult(self):
        self.panel.clearContent()

    # ── Selección ──────────────────────────────────────────────

    def _set_selection_buttons(self, enabled):
        self.panel.btnEditarSeleccion.setEnabled(enabled)
        self.panel.btnEliminarSeleccion.setEnabled(enabled)
        self.actEditar.setEnabled(enabled)
        self.actEliminar.setEnabled(enabled)

    def updateSelectionInfo(self):
        lienzo = self.lienzo
        graph = lienzo.graph
        selected_node = lienzo.selected_node
        selected_edge = lienzo.selected_edge
        selected_nodes = lienzo.selected_nodes
        selected_edges = lienzo.selected_edges

        if selected_nodes or selected_edges:
            partes = []
            if selected_nodes:
                partes.append(
                    f"Nodos seleccionados ({len(selected_nodes)}): {', '.join(map(str, sorted(selected_nodes)))}"
                )
            if selected_edges:
                partes.append(
                    f"Aristas seleccionadas ({len(selected_edges)}): "
                    + "; ".join(f"{u} -> {v}" for u, v in sorted(selected_edges))
                )
            self.panel.setSelectionInfo("\n".join(partes))
            self._set_selection_buttons(True)
            self.actEditar.setEnabled(selected_node is not None or selected_edge is not None)
            return

        if selected_node is not None:
            position = lienzo.pos.get(selected_node)
            degree = graph.degree(selected_node)

            if graph.is_directed():
                predecessors = sorted(graph.predecessors(selected_node))
                successors = sorted(graph.successors(selected_node))
                details = (
                    f"Nodo seleccionado: {selected_node}\n"
                    f"Grado total: {degree} (entrada {graph.in_degree(selected_node)}, "
                    f"salida {graph.out_degree(selected_node)})\n"
                    f"Predecesores: {', '.join(map(str, predecessors)) if predecessors else 'Ninguno'}\n"
                    f"Sucesores: {', '.join(map(str, successors)) if successors else 'Ninguno'}"
                )
            else:
                neighbors = sorted(graph.neighbors(selected_node))
                details = (
                    f"Nodo seleccionado: {selected_node}\n"
                    f"Grado: {degree}\n"
                    f"Vecinos: {', '.join(map(str, neighbors)) if neighbors else 'Ninguno'}"
                )

            if position is not None:
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
                f"Tipo: {tipo}\n"
                "Doble clic sobre la arista para editar su peso."
            )
            self._set_selection_buttons(True)
            return

        self.panel.clearSelectionInfo()
        self._set_selection_buttons(False)

    def handleSelectionEdit(self):
        if self.lienzo.selected_node is not None:
            self.editarNodoSeleccionado()
        elif self.lienzo.selected_edge is not None:
            self.editarPesoArista(*self.lienzo.selected_edge)

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
