from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QLabel, QPushButton, QScrollArea, QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)

from ui import theme
from ui.player import ReproductorPasos

TEXTO_SIN_SELECCION = "Selecciona un nodo o una arista para ver sus propiedades."
TEXTO_SIN_RESULTADO = "Ejecuta un algoritmo desde el menú Algoritmos o con clic derecho sobre un nodo."


class Seccion(QWidget):
    """Bloque con encabezado que se puede plegar."""

    def __init__(self, titulo, parent=None):
        super().__init__(parent)
        self.encabezado = QToolButton()
        self.encabezado.setObjectName("encabezadoSeccion")
        self.encabezado.setText(titulo)
        self.encabezado.setCheckable(True)
        self.encabezado.setChecked(True)
        self.encabezado.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.encabezado.setArrowType(Qt.ArrowType.DownArrow)
        self.encabezado.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.encabezado.toggled.connect(self._alternar)

        self.contenido = QWidget()
        self.layout_contenido = QVBoxLayout(self.contenido)
        self.layout_contenido.setContentsMargins(4, 6, 4, 4)
        self.layout_contenido.setSpacing(8)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.encabezado)
        layout.addWidget(self.contenido)

    def agregar(self, widget):
        self.layout_contenido.addWidget(widget)
        return widget

    @property
    def expandida(self):
        return self.encabezado.isChecked()

    def _alternar(self, expandida):
        self.encabezado.setArrowType(Qt.ArrowType.DownArrow if expandida else Qt.ArrowType.RightArrow)
        self.contenido.setVisible(expandida)


class Panel(QWidget):
    """Panel lateral: selección, resultado del algoritmo y resumen del grafo."""

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.scrollarea = QScrollArea(self)
        self.scrollarea.setWidgetResizable(True)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(10)

        # Selección
        self.seccionSeleccion = Seccion("Selección")
        self.selection_label = self.seccionSeleccion.agregar(self._crear_label(TEXTO_SIN_SELECCION))

        # Algoritmo
        self.seccionAlgoritmo = Seccion("Algoritmo")
        self.algorithm_label = self.seccionAlgoritmo.agregar(self._crear_label(""))
        self.algorithm_label.setObjectName("tituloAlgoritmo")
        self.reproductor = self.seccionAlgoritmo.agregar(ReproductorPasos())
        self.legend_label = self.seccionAlgoritmo.agregar(self._crear_label(""))
        self.legend_label.setObjectName("leyenda")
        self.legend_label.setTextFormat(Qt.TextFormat.RichText)
        self.content_label = self.seccionAlgoritmo.agregar(self._crear_label(TEXTO_SIN_RESULTADO))
        self.content_label.setObjectName("resumenAlgoritmo")
        self.content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.btnLimpiarAnalisis = self.seccionAlgoritmo.agregar(QPushButton("Quitar resultado"))

        # Grafo
        self.seccionGrafo = Seccion("Grafo")
        self.stats_label = self.seccionGrafo.agregar(self._crear_label("Resumen del grafo:"))
        self.view_label = self.seccionGrafo.agregar(self._crear_label("Vista actual: Todo"))

        titulo_font = QFont()
        titulo_font.setPointSize(13)
        titulo_font.setBold(True)
        self.algorithm_label.setFont(titulo_font)

        mono_font = QFont("Consolas")
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        mono_font.setPointSize(10)
        self.content_label.setFont(mono_font)

        for seccion in (self.seccionSeleccion, self.seccionAlgoritmo, self.seccionGrafo):
            self.scroll_layout.addWidget(seccion)
        self.scroll_layout.addStretch()

        self.scrollarea.setWidget(self.scroll_content)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scrollarea)
        self.setLayout(layout)

        self.clearContent()

    @staticmethod
    def _crear_label(texto):
        label = QLabel(texto)
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        label.setWordWrap(True)
        return label

    # ── Resultado del algoritmo ────────────────────────────────

    def setResultado(self, nombre, resumen, pasos=()):
        self.algorithm_label.setText(nombre)
        self.algorithm_label.setVisible(bool(nombre))
        self.content_label.setText(resumen)
        self.btnLimpiarAnalisis.setVisible(bool(nombre))
        self.seccionAlgoritmo.encabezado.setChecked(True)
        self.reproductor.cargar(list(pasos))

    def clearContent(self):
        self.setResultado("", TEXTO_SIN_RESULTADO)
        self.setLeyenda(None)

    def setLeyenda(self, estado):
        """Muestra solo los colores que aparecen en el estado actual."""
        if estado is None:
            self.legend_label.setVisible(False)
            return

        presentes_nodos = set(estado.nodos.values())
        presentes_aristas = set(estado.aristas.values())
        filas = []
        for clave, texto in theme.LEYENDA_NODOS:
            if clave in presentes_nodos:
                relleno, borde = theme.ESTADOS_NODO[clave]
                filas.append(f'<span style="color:{relleno}; font-size:15px;">●</span>&nbsp;{texto}')
        if estado.usa_estados_de_nodo:
            filas.append(f'<span style="color:{theme.NODO_PENDIENTE[1]}; font-size:15px;">●</span>&nbsp;Pendiente')
        for clave, texto in theme.LEYENDA_ARISTAS:
            if clave in presentes_aristas:
                estilo = theme.ESTADOS_ARISTA[clave]
                trazo = '╍╍' if estilo['estilo'] == 'dashed' else '━━'
                filas.append(f'<span style="color:{estilo["color"]}; font-weight:bold;">{trazo}</span>&nbsp;{texto}')

        self.legend_label.setText("<br>".join(filas))
        self.legend_label.setVisible(bool(filas))

    # ── Selección y estadísticas ───────────────────────────────

    def setSelectionInfo(self, newcontent):
        self.selection_label.setText(newcontent)

    def clearSelectionInfo(self):
        self.selection_label.setText(TEXTO_SIN_SELECCION)

    def setStats(self, newcontent):
        self.stats_label.setText(newcontent)

    def setViewInfo(self, newcontent):
        self.view_label.setText(newcontent)
