from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, 
    QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox
)
from PyQt6.QtGui import QIntValidator
from PyQt6.QtCore import Qt

class MiDialogo(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.valor1 = None
        self.valor2 = None
        self.valor3 = None
        self.setWindowTitle('Ingresar Valores')

        # --- LAYOUT PRINCIPAL ---
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- FORMULARIO ---
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Estilo común para etiquetas
        label_style = "font-weight: bold; color: #2c3e50; font-size: 13px;"

        self.label1 = QLabel("Nodo Origen:")
        self.label1.setStyleSheet(label_style)
        self.entrada1 = QLineEdit()
        self.entrada1.setValidator(QIntValidator())
        self.entrada1.setPlaceholderText("Ej. 1")
        form_layout.addRow(self.label1, self.entrada1)

        self.label2 = QLabel("Nodo Destino:")
        self.label2.setStyleSheet(label_style)
        self.entrada2 = QLineEdit()
        self.entrada2.setValidator(QIntValidator())
        self.entrada2.setPlaceholderText("Ej. 2")
        form_layout.addRow(self.label2, self.entrada2)

        self.label3 = QLabel("Peso / Costo:")
        self.label3.setStyleSheet(label_style)
        self.entrada3 = QLineEdit()
        self.entrada3.setValidator(QIntValidator())
        self.entrada3.setPlaceholderText("Ej. 5")
        form_layout.addRow(self.label3, self.entrada3)

        main_layout.addLayout(form_layout)

        # --- BOTONES ---
        button_layout = QHBoxLayout()
        
        self.btnGuardar = QPushButton("Guardar Arista")
        self.btnGuardar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnGuardar.clicked.connect(self.Guardar)
        
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

    def Guardar(self):
        # Obtener los valores de los QLineEdit
        valor1 = self.entrada1.text().strip()
        valor2 = self.entrada2.text().strip()
        valor3 = self.entrada3.text().strip()

        # Almacenar los valores como atributos de la instancia
        if valor1 != '' and valor2 != '' and valor3 != '':
            self.valor1 = valor1
            self.valor2 = valor2
            self.valor3 = valor3
            self.accept()
        else:
            alerta = QMessageBox()
            alerta.setIcon(QMessageBox.Icon.Warning)
            alerta.setText("Error")
            alerta.setInformativeText("Ingrese todos los datos correctos.")
            alerta.setWindowTitle("Alerta")
            alerta.exec()
