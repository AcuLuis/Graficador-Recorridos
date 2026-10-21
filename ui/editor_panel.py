from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QSizePolicy, QVBoxLayout, QWidget,
)

from ui.canvas import Lienzo
from ui.dialogs import DialogoArista, DialogoNodo


class PanelVista(QWidget):
    """Zona central: tipo de grafo, herramientas de edición y lienzo."""

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
            cbzBotones_layout.addWidget(boton, index // 6, index % 6)

        for columna in range(6):
            cbzBotones_layout.setColumnStretch(columna, 1)
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
        self.toolbar = NavigationToolbar(self.lienzo.canvas, self)
        self.lienzo.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        grafoUI_layout = QVBoxLayout()
        grafoUI_layout.addWidget(self.toolbar)
        grafoUI_layout.addWidget(self.lienzo.canvas, stretch=1)
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
        canvas = self.lienzo.canvas
        canvas.mpl_disconnect(self.lienzo.cid)
        if state:
            self.btnDibujar.setEnabled(True)
        else:
            self.lienzo.cid = canvas.mpl_connect('button_press_event', self.lienzo.MouseClick)
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

    def buildGraphSummaryText(self):
        return self.parent().buildGraphSummaryText()

    def PideNodos(self):
        dialogo = DialogoArista(self)
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
        nodo = self.solicitarNodoSecundario("Eliminar Nodo", "Ingresa el ID del Nodo a eliminar:")
        if nodo is not None:
            self.lienzo.eliminarNodo(nodo)

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

        dialogo = DialogoArista(self, titulo='Editar Peso de Arista')
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
