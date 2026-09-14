from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, 
    QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox
)
from PyQt6.QtGui import QIntValidator
from PyQt6.QtCore import Qt

class DialogoNodo(QDialog):
    """Diálogo genérico para solicitar un ID de nodo."""
    def __init__(self, titulo="Ingresar Nodo", mensaje="Ingresa ID del Nodo:", parent=None):
        super().__init__(parent)
        self.valor1 = None
        self.setWindowTitle(titulo)
        
        # --- LAYOUT PRINCIPAL ---
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- FORMULARIO ---
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        label_style = "font-weight: bold; color: #2c3e50; font-size: 13px;"

        self.label1 = QLabel(mensaje)
        self.label1.setStyleSheet(label_style)
        self.entrada1 = QLineEdit()
        self.edit1 = self.entrada1
        self.entrada1.setValidator(QIntValidator())
        self.entrada1.setPlaceholderText("Ej. 1")
        form_layout.addRow(self.label1, self.entrada1)

        main_layout.addLayout(form_layout)

        # --- BOTONES ---
        button_layout = QHBoxLayout()
        
        self.btnGuardar = QPushButton("Aceptar")
        self.btnGuardar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnGuardar.clicked.connect(self.aceptar_valores)
        
        self.btnCancelar = QPushButton("Cancelar")
        self.btnCancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnCancelar.clicked.connect(self.Cancelar)
        
        button_layout.addStretch()
        button_layout.addWidget(self.btnCancelar)
        button_layout.addWidget(self.btnGuardar)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)

    def Cancelar(self):
        self.reject()

    def aceptar_valores(self):
        # Obtener los valores de los QLineEdit
        valor1 = self.entrada1.text().strip()
        
        if valor1:
            self.valor1 = valor1
            # Cerrar el cuadro de diálogo con aceptación
            self.accept()
        else:
            alerta = QMessageBox(self)
            alerta.setIcon(QMessageBox.Icon.Warning)
            alerta.setText("Error")
            alerta.setInformativeText("Ingrese un ID válido.")
            alerta.setWindowTitle("Alerta")
            alerta.exec()