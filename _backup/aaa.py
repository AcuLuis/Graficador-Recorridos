import sys
import networkx as nx
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene, QLabel, QPushButton, QFrame, QRadioButton
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
from Arista import MiDialogo

class Node:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class Lienzo:
    def __init__(self, main_window):
        self.main_window = main_window
        self.graph = nx.Graph()
        self.pos = {}
        self.fig, self.ax = plt.subplots()
        self.cid = self.fig.canvas.mpl_connect('button_press_event', self.MouseClick)
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.axis('off')  # Desactivar ejes
        self.rect = plt.Rectangle((0, 0), 1, 1, linewidth=2, edgecolor='black', facecolor='none')
        self.ax.add_patch(self.rect)

    def DibujarArista(self, posNodo1, posNodo2):
        print(f"HOLIS: {posNodo1} , {posNodo2}")
        self.graph.add_edge(posNodo1, posNodo2)
        self.DibujarGrafo()

    def MouseClick(self, event):
        print("Click")
        if event.xdata is not None and event.ydata is not None:
            if self.main_window.dibNodoIsSelected():
                node_id = len(self.graph.nodes) + 1
                self.graph.add_node(node_id)
                self.pos[node_id] = (event.xdata, event.ydata)
                if self.main_window.dibNodoIsSelected():
                    self.DibujarGrafo()
                else:
                    print()

    def DibujarGrafo(self):
        # Guardar temporalmente el color del borde del rectángulo
        original_edgecolor = self.rect.get_edgecolor()
        self.ax.clear()
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.axis('off')  # Desactivar ejes
        self.rect = plt.Rectangle((0, 0), 1, 1, linewidth=2, edgecolor='black', facecolor='none')
        self.ax.add_patch(self.rect)

        # Dibujar el grafo después de restaurar el color del borde
        nx.draw(self.graph, pos=self.pos, with_labels=True, font_weight='bold', ax=self.ax)

        # Restaurar el color del borde original
        self.rect.set_edgecolor(original_edgecolor)

        plt.draw()

    def Limpiar(self):
        self.graph.clear()
        self.pos = {}
        self.DibujarGrafo()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Crear contenedor vertical para contResults y contLienzo
        contResultsLienzo = QWidget()
        contResultsLienzo_layout = QHBoxLayout(contResultsLienzo)

        # Crear contenedor vertical para contTipoGrafo y contOpciones
        contTipoGrafoOpciones = QWidget()
        contTipoGrafoOpciones_layout = QVBoxLayout(contTipoGrafoOpciones)

        # Crear contenedor vertical para contTipoGrafo
        contTipoGrafo = QWidget()
        contTipoGrafo_layout = QVBoxLayout(contTipoGrafo)

        # Agregar algunos botones a contTipoGrafo 
        labelGrafo = QLabel("Puedes:")
        labelAnchura = QLabel("Búsqueda En Anchura.")
        labelProfundidad = QLabel("Búsqueda En Profundidad.")
        labelDikstra = QLabel("Algoritmo de Dikstra.")
        labelKruskal = QLabel("Algoritmo de Kruskal.")
    
        
        # Establecer por defecto la selección del radiobutton 'Si'

        contTipoGrafo_layout.addWidget(labelGrafo)
        contTipoGrafo_layout.addWidget(labelAnchura)
        contTipoGrafo_layout.addWidget(labelProfundidad)
        contTipoGrafo_layout.addWidget(labelDikstra)
        contTipoGrafo_layout.addWidget(labelKruskal)

        # Conectar señales y ranuras para habilitar/deshabilitar opciones

        # Agregar contTipoGrafo a contTipoGrafoOpciones
        contTipoGrafoOpciones_layout.addWidget(contTipoGrafo)

        # Crear contenedor vertical para contOpciones
        contOpciones = QWidget()
        contOpciones_layout = QVBoxLayout(contOpciones)

        # Agregar algunos botones a contTipoGrafo 
        labelGrafo = QLabel("Opciones: ")
        self.rbDibNodo = QRadioButton('Dibujar Nodo')
        self.rbDibArista = QRadioButton('Dibujar Arista')
        self.btnDibujar = QPushButton('Ingresar Puntos')

        # Asignar un nombre específico a cada radio button
        self.rbDibArista.setObjectName('rbDibArista')

        # Establecer por defecto la selección del radiobutton 'Dibujar Nodo'
        self.rbDibNodo.setChecked(True)
        self.btnDibujar.setEnabled(False)

        contOpciones_layout.addWidget(labelGrafo)
        contOpciones_layout.addWidget(self.rbDibNodo)
        contOpciones_layout.addWidget(self.rbDibArista)
        contOpciones_layout.addWidget(self.btnDibujar)


        # Agregar contOpciones a contTipoGrafoOpciones
        contTipoGrafoOpciones_layout.addWidget(contOpciones)

        # Agregar contTipoGrafoOpciones a la capa principal
        contResultsLienzo_layout.addWidget(contTipoGrafoOpciones)

        # Agregar línea divisoria vertical entre contTipoGrafoOpciones y contResults
        line1 = QFrame(self)
        line1.setFrameShape(QFrame.VLine)
        line1.setFrameShadow(QFrame.Sunken)
        contResultsLienzo_layout.addWidget(line1)

        # Crear contenedor vertical para contResults
        contResults = QWidget()
        contResults_layout = QVBoxLayout(contResults)

        # Agregar widgets al contenedor de resultados
        label1 = QLabel('Resultados')
        btnLimpiar = QPushButton('Limpiar')
        contResults_layout.addWidget(label1)
        contResults_layout.addWidget(btnLimpiar)
        btnLimpiar.clicked.connect(self.LimpiarLienzo)

        # Tamaño fijo para el contenedor1
        contResults.setFixedWidth(300)

        # Agregar contResults a la capa principal
        contResultsLienzo_layout.addWidget(contResults)

        # Agregar línea divisoria vertical entre contResults y contLienzo
        line2 = QFrame(self)
        line2.setFrameShape(QFrame.VLine)
        line2.setFrameShadow(QFrame.Sunken)
        contResultsLienzo_layout.addWidget(line2)

        # Crear contenedor vertical para contLienzo
        contLienzo = QWidget()
        contLienzo_layout = QVBoxLayout(contLienzo)

        contLienzo.setMinimumWidth(500)
        contLienzo.setMinimumHeight(500)

        # Agregar widgets al contenedor del Lienzo
        label2 = QLabel('Lienzo')
        contLienzo_layout.addWidget(label2)

        # Crear instancia de la clase Lienzo y agregarla al contenedor del Lienzo
        # Create instance of the Lienzo class and pass self as an argument
        self.lienzo = Lienzo(self)
        contLienzo_layout.addWidget(self.lienzo.fig.canvas)

        # Agregar contLienzo a la capa principal
        contResultsLienzo_layout.addWidget(contLienzo)

        # Configurar el diseño de la ventana principal
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(contResultsLienzo)

        self.setGeometry(100, 100, 800, 400)
        self.setWindowTitle('Grafos')

        # Conectar la función onRadioButtonToggled al evento toggled de rbDibArista
        self.rbDibArista.toggled.connect(lambda state=self.rbDibArista.isChecked(): self.onRadioButtonToggled(state))
        self.btnDibujar.clicked.connect(self.PideNodos)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def add_node(self, node):
        # Agregar el nodo al grafo y actualizar el gráfico
        node_id = len(self.lienzo.graph.nodes) + 1
        self.lienzo.graph.add_node(node_id)
        self.lienzo.pos[node_id] = (node.x, node.y)
        self.lienzo.DibujarGrafo()

    def onRadioButtonToggled(self, state):
        # Verificar si rbDibArista está seleccionado
        if state:
            # Asignar la función DibujarArista al evento 'button_press_event'
            self.lienzo.fig.canvas.mpl_disconnect(self.lienzo.cid)
            self.lienzo.cid = self.lienzo.fig.canvas.mpl_connect('button_press_event', self.lienzo.MouseClick)
            self.btnDibujar.setEnabled(True)
        else:
            # Restaurar la función MouseClick al evento 'button_press_event'
            self.lienzo.fig.canvas.mpl_disconnect(self.lienzo.cid)
            self.lienzo.cid = self.lienzo.fig.canvas.mpl_connect('button_press_event', self.MouseClickArista)
            self.btnDibujar.setEnabled(False)

    def dibNodoIsSelected(self):
        if self.btnDibujar.isEnabled():
            return False
        return True

    def MouseClickArista(self, event):
        if event.xdata is not None and event.ydata is not None:
            if len(self.lienzo.graph.nodes) == 2:
                nodes = list(self.lienzo.graph.nodes)
                node1 = nodes[0]
                node2 = nodes[1]
                self.lienzo.DibujarArista(node1, node2)
                # Restore the original MouseClick behavior
                self.lienzo.fig.canvas.mpl_disconnect(self.lienzo.cid)
                self.lienzo.cid = self.lienzo.fig.canvas.mpl_connect('button_press_event', self.lienzo.MouseClick)

    def PideNodos(self):
        dialogo = MiDialogo()
        resultado = dialogo.exec_()
        
        if resultado == QDialog.Accepted:
            valor1 = dialogo.valor1
            valor2 = dialogo.valor2
            self.lienzo.DibujarArista(int(valor1), int(valor2))

        

    def LimpiarLienzo(self):
        self.lienzo.Limpiar()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
