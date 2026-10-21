from PyQt6.QtCore import QLocale, Qt
from PyQt6.QtGui import QDoubleValidator, QIntValidator
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout,
)

LABEL_STYLE = "font-weight: bold; color: #2c3e50; font-size: 13px;"


class _DialogoFormulario(QDialog):
    """Base de los diálogos: formulario + botones Cancelar/Aceptar."""

    def __init__(self, titulo, texto_aceptar, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)

        self._main_layout = QVBoxLayout()
        self._main_layout.setContentsMargins(20, 20, 20, 20)
        self._main_layout.setSpacing(15)

        self.form_layout = QFormLayout()
        self.form_layout.setSpacing(10)
        self._main_layout.addLayout(self.form_layout)

        button_layout = QHBoxLayout()
        self.btnGuardar = QPushButton(texto_aceptar)
        self.btnGuardar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnGuardar.setDefault(True)
        self.btnGuardar.clicked.connect(self.Guardar)

        self.btnCancelar = QPushButton("Cancelar")
        self.btnCancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnCancelar.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.btnCancelar)
        button_layout.addWidget(self.btnGuardar)
        self._main_layout.addLayout(button_layout)

        self.setLayout(self._main_layout)

    def _agregar_campo(self, etiqueta, placeholder, validator):
        label = QLabel(etiqueta)
        label.setStyleSheet(LABEL_STYLE)
        entrada = QLineEdit()
        entrada.setValidator(validator)
        entrada.setPlaceholderText(placeholder)
        self.form_layout.addRow(label, entrada)
        return entrada

    def _alerta(self, mensaje):
        alerta = QMessageBox(self)
        alerta.setIcon(QMessageBox.Icon.Warning)
        alerta.setText("Error")
        alerta.setInformativeText(mensaje)
        alerta.setWindowTitle("Alerta")
        alerta.exec()

    def Guardar(self):
        raise NotImplementedError


class DialogoArista(_DialogoFormulario):
    """Solicita origen, destino y peso de una arista."""

    def __init__(self, parent=None, titulo="Ingresar Valores"):
        super().__init__(titulo, "Guardar Arista", parent)
        self.valor1 = None
        self.valor2 = None
        self.valor3 = None

        self.entrada1 = self._agregar_campo("Nodo Origen:", "Ej. 1", QIntValidator())
        self.entrada2 = self._agregar_campo("Nodo Destino:", "Ej. 2", QIntValidator())
        self.entrada3 = self._agregar_campo("Peso / Costo:", "Ej. 5", QIntValidator())

    def Guardar(self):
        valor1 = self.entrada1.text().strip()
        valor2 = self.entrada2.text().strip()
        valor3 = self.entrada3.text().strip()

        if valor1 != '' and valor2 != '' and valor3 != '':
            self.valor1 = valor1
            self.valor2 = valor2
            self.valor3 = valor3
            self.accept()
        else:
            self._alerta("Ingrese todos los datos correctos.")


class DialogoNodo(_DialogoFormulario):
    """Diálogo genérico para solicitar un ID de nodo."""

    def __init__(self, titulo="Ingresar Nodo", mensaje="Ingresa ID del Nodo:", parent=None,
                 valor_inicial=None, opcional=False):
        super().__init__(titulo, "Aceptar", parent)
        self.valor1 = None
        self.opcional = opcional
        placeholder = "Opcional" if opcional else "Ej. 1"
        self.entrada1 = self._agregar_campo(mensaje, placeholder, QIntValidator())
        if valor_inicial is not None:
            self.entrada1.setText(str(valor_inicial))
            self.entrada1.selectAll()

    def Guardar(self):
        valor1 = self.entrada1.text().strip()

        if valor1 or self.opcional:
            self.valor1 = valor1
            self.accept()
        else:
            self._alerta("Ingrese un ID válido.")


class DialogoPosicion(_DialogoFormulario):
    """Edita la posición (x, y) de un nodo."""

    def __init__(self, nodo, posicion, parent=None):
        super().__init__(f"Editar nodo {nodo}", "Guardar", parent)
        self.posicion = None

        self.entrada_x = self._agregar_campo("Posición X:", "Ej. 0.5", self._validador_decimal())
        self.entrada_y = self._agregar_campo("Posición Y:", "Ej. 0.5", self._validador_decimal())
        self.entrada_x.setText(f"{posicion[0]:.4f}")
        self.entrada_y.setText(f"{posicion[1]:.4f}")

    def _validador_decimal(self):
        # Locale C: se acepta el punto decimal sin importar la configuración regional.
        validador = QDoubleValidator(self)
        validador.setLocale(QLocale.c())
        validador.setNotation(QDoubleValidator.Notation.StandardNotation)
        return validador

    def Guardar(self):
        try:
            x = float(self.entrada_x.text().replace(',', '.'))
            y = float(self.entrada_y.text().replace(',', '.'))
        except ValueError:
            self._alerta("Las posiciones deben ser números válidos.")
            return

        self.posicion = (x, y)
        self.accept()
