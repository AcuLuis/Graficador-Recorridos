from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

TEXTO_SIN_SELECCION = "Selecciona un nodo o una arista para ver sus propiedades."
TEXTO_SIN_RESULTADO = "Ejecuta un algoritmo para ver los pasos."


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

        self.selection_label = self._crear_label(TEXTO_SIN_SELECCION)
        self.stats_label = self._crear_label("Resumen del grafo:")
        self.view_label = self._crear_label("Vista actual: Todo")
        self.content_label = self._crear_label(TEXTO_SIN_RESULTADO)
        self.content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.help_label = self._crear_label(
            "Ayuda rápida:\n"
            "• Click en el lienzo para crear nodos cuando está activo 'Dibujar Nodo'.\n"
            "• Ctrl/Shift + click para seleccionar varios nodos o aristas.\n"
            "• Botón central del mouse para desplazar la vista.\n"
            "• Usa 'Ocultar aislados' o 'Componente actual' para enfocar análisis."
        )

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

    @staticmethod
    def _crear_label(texto):
        label = QLabel(texto)
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        label.setWordWrap(True)
        return label

    def setContent(self, newcontent):
        self.content_label.setText(newcontent)

    def clearContent(self):
        self.content_label.setText(TEXTO_SIN_RESULTADO)

    def setSelectionInfo(self, newcontent):
        self.selection_label.setText(newcontent)

    def setStats(self, newcontent):
        self.stats_label.setText(newcontent)

    def setViewInfo(self, newcontent):
        self.view_label.setText(newcontent)

    def clearSelectionInfo(self):
        self.selection_label.setText(TEXTO_SIN_SELECCION)
