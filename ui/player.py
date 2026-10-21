from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QSlider, QToolButton, QVBoxLayout, QWidget,
)

VELOCIDAD_INICIAL = 3   # pasos por segundo
VELOCIDAD_MAXIMA = 10


class ReproductorPasos(QWidget):
    """Controles para recorrer los pasos de un algoritmo.

    La posición va de 0 (ningún paso aplicado) a n (todos aplicados, que
    equivale al resultado final). Emite pasoCambiado(posicion).
    """

    pasoCambiado = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.total = 0
        self.posicion = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._avanzarAutomatico)

        self.btnInicio = self._boton("⇤", "Ir al inicio (antes del primer paso)", self.irAlInicio)
        self.btnAnterior = self._boton("←", "Paso anterior", self.anterior)
        self.btnReproducir = self._boton("▶", "Reproducir / pausar", self.alternarReproduccion)
        self.btnSiguiente = self._boton("→", "Paso siguiente", self.siguiente)
        self.btnFinal = self._boton("⇥", "Ir al resultado final", self.irAlFinal)

        controles = QHBoxLayout()
        controles.setSpacing(4)
        for boton in (self.btnInicio, self.btnAnterior, self.btnReproducir, self.btnSiguiente, self.btnFinal):
            controles.addWidget(boton)
        controles.addStretch()

        self.lblPosicion = QLabel()
        self.lblPosicion.setObjectName("posicionPaso")

        self.sliderVelocidad = QSlider(Qt.Orientation.Horizontal)
        self.sliderVelocidad.setRange(1, VELOCIDAD_MAXIMA)
        self.sliderVelocidad.setValue(VELOCIDAD_INICIAL)
        self.sliderVelocidad.setToolTip("Velocidad de reproducción (pasos por segundo)")
        self.sliderVelocidad.valueChanged.connect(self._actualizarIntervalo)
        self.filaVelocidad = QWidget()
        velocidad = QHBoxLayout(self.filaVelocidad)
        velocidad.setContentsMargins(0, 0, 0, 0)
        velocidad.addWidget(QLabel("Velocidad"))
        velocidad.addWidget(self.sliderVelocidad)

        self.filaControles = QWidget()
        self.filaControles.setLayout(controles)
        controles.setContentsMargins(0, 0, 0, 0)

        self.lista = QListWidget()
        self.lista.setObjectName("listaPasos")
        self.lista.setMinimumHeight(180)
        self.lista.setWordWrap(True)
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lista.itemClicked.connect(self._pasoElegido)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.filaControles)
        layout.addWidget(self.lblPosicion)
        layout.addWidget(self.filaVelocidad)
        layout.addWidget(self.lista)

        self._actualizarIntervalo()
        self.cargar([])

    def _boton(self, texto, ayuda, slot):
        boton = QToolButton()
        boton.setObjectName("botonReproductor")
        boton.setText(texto)
        boton.setToolTip(ayuda)
        boton.setMinimumWidth(36)
        boton.clicked.connect(slot)
        return boton

    # ── Carga y navegación ─────────────────────────────────────

    def cargar(self, pasos):
        """Carga los pasos y se ubica en el resultado final."""
        self.pausar()
        self.total = len(pasos)
        self.lista.clear()
        for numero, paso in enumerate(pasos, start=1):
            item = QListWidgetItem(f"{numero}. {paso.texto.strip()}")
            item.setData(Qt.ItemDataRole.UserRole, numero)
            self.lista.addItem(item)

        hay_pasos = self.total > 0
        for widget in (self.filaControles, self.lblPosicion, self.filaVelocidad, self.lista):
            widget.setVisible(hay_pasos)
        self.irA(self.total)

    def irA(self, posicion):
        self.posicion = max(0, min(posicion, self.total))
        self._actualizarControles()
        self.pasoCambiado.emit(self.posicion)

    def irAlInicio(self):
        self.pausar()
        self.irA(0)

    def irAlFinal(self):
        self.pausar()
        self.irA(self.total)

    def anterior(self):
        self.pausar()
        self.irA(self.posicion - 1)

    def siguiente(self):
        self.pausar()
        self.irA(self.posicion + 1)

    def _pasoElegido(self, item):
        self.pausar()
        self.irA(item.data(Qt.ItemDataRole.UserRole))

    # ── Reproducción automática ────────────────────────────────

    @property
    def reproduciendo(self):
        return self.timer.isActive()

    def alternarReproduccion(self):
        if self.reproduciendo:
            self.pausar()
            return
        if self.posicion >= self.total:
            self.irA(0)
        self.timer.start()
        self._actualizarControles()

    def pausar(self):
        self.timer.stop()
        self._actualizarControles()

    def _avanzarAutomatico(self):
        if self.posicion >= self.total:
            self.pausar()
            return
        self.irA(self.posicion + 1)
        if self.posicion >= self.total:
            self.pausar()

    def _actualizarIntervalo(self):
        self.timer.setInterval(int(1000 / self.sliderVelocidad.value()))

    def _actualizarControles(self):
        self.btnReproducir.setText("❚❚" if self.reproduciendo else "▶")
        self.btnInicio.setEnabled(self.posicion > 0)
        self.btnAnterior.setEnabled(self.posicion > 0)
        self.btnSiguiente.setEnabled(self.posicion < self.total)
        self.btnFinal.setEnabled(self.posicion < self.total)

        if self.posicion == 0:
            self.lblPosicion.setText(f"Inicio · {self.total} pasos")
        elif self.posicion >= self.total:
            self.lblPosicion.setText(f"Resultado final · {self.total} pasos")
        else:
            self.lblPosicion.setText(f"Paso {self.posicion} de {self.total}")

        self.lista.blockSignals(True)
        if 0 < self.posicion <= self.total:
            self.lista.setCurrentRow(self.posicion - 1)
            self.lista.scrollToItem(self.lista.currentItem())
        else:
            self.lista.clearSelection()
            self.lista.setCurrentRow(-1)
        self.lista.blockSignals(False)
