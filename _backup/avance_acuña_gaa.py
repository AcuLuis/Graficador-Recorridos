from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
import networkx as nx
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene, QLabel, QPushButton, QFrame, QRadioButton
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
from Arista import MiDialogo
from matplotlib.patches import FancyArrow
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt5.QtWidgets import QScrollBar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from Utilidades import Operaciones as op
from collections import deque
from PyQt5.QtWidgets import QMessageBox

centralWidget = None
panel = None
ancho = None
altura = None
posX = None
posY = None
TipoGrafo="NoDirigido"
verifica = None
class Lienzo:
    def __init__(self, main_window):
        self.main_window = main_window    
        self.graph = nx.Graph()
        self.edge_colors={}
        self.edge_weights = {} 
        self.pos = {}
        self.fig, self.ax = plt.subplots()
        self.cid = self.fig.canvas.mpl_connect('button_press_event', self.MouseClick)
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.axis('off')
        self.rect = plt.Rectangle((0,0), 1, 1, linewidth=2, edgecolor='black', facecolor='none')
        self.ax.add_patch(self.rect)
    def setTipoGrafo(self, tipo):
        if(tipo=="Dirigido"):
            self.graph=nx.DiGraph()
        if(tipo=="NoDirigido"):
            self.graph=nx.Graph()
    def DibujarArista(self, posNodo1, posNodo2,peso=1):
        if posNodo1 in self.graph.nodes() and posNodo2 in self.graph.nodes():
            self.graph.add_edge(posNodo1, posNodo2,weight=peso)
            self.edge_colors[(posNodo1, posNodo2)] = "black"
            self.edge_weights[(posNodo1, posNodo2)] = peso
            self.DibujarGrafo()
        else:
            if posNodo1 not in self.graph.nodes():
                msg = f"El nodo {posNodo1} no se encuentra."
            if posNodo2 not in self.graph.nodes():
                msg = f"El nodo {posNodo2} no se encuentra."
            if posNodo1 not in self.graph.nodes() and posNodo2 not in self.graph.nodes(): 
                msg = "Los nodos no se encuentran."
            self.Alertas(msg)
    def Alertas(self, mensaje):
        alerta = QMessageBox()
        alerta.setIcon(QMessageBox.Warning)
        if mensaje == "Cambiando tipo de grafo.":
            alerta.setText('Se borrará tu avance. \n ¿Estás seguro de continuar?')
            alerta.setWindowTitle('Alerta')
            btnSi = alerta.addButton('Sí', QMessageBox.YesRole)
            btnNo = alerta.addButton('Cancelar', QMessageBox.NoRole)
            alerta.exec_()
            if alerta.clickedButton() == btnSi:
                self.Limpiar()
                return True
            elif alerta.clickedButton() == btnNo:
                return False
        else:
            alerta.setText("Elemento no encontrado")
            alerta.setInformativeText(mensaje)
            alerta.setWindowTitle("Alerta")
            alerta.exec_()
    def MouseClick(self, event):
        if event.xdata is not None and event.ydata is not None:
            if self.main_window.dibNodoIsSelected():
                node_id = len(self.graph.nodes) + 1
                self.graph.add_node(node_id)
                self.pos[node_id] = (event.xdata, event.ydata)
                if self.main_window.dibNodoIsSelected():
                    self.DibujarGrafo()
    def DibujarGrafo(self):
        edge_labels = nx.get_edge_attributes(self.graph, 'weight')
        original_edgecolor = self.rect.get_edgecolor()
        self.ax.clear()
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.axis('off')
        self.rect = plt.Rectangle((0, 0), 1, 1, linewidth=2, edgecolor='black', facecolor='none')
        self.ax.add_patch(self.rect)
        if( not self.edge_colors and not self.edge_weights):
             nx.draw(self.graph, pos=self.pos, with_labels=True, font_weight='bold', ax=self.ax)
             nx.draw_networkx_edge_labels(self.graph, pos=self.pos, edge_labels=edge_labels, ax=self.ax)
        else:
            nx.draw(self.graph, pos=self.pos, with_labels=True, font_weight='bold', ax=self.ax,
                edge_color=[self.edge_colors.get(edge, 'black') for edge in self.graph.edges()])
            nx.draw_networkx_edge_labels(self.graph, pos=self.pos, edge_labels=edge_labels, ax=self.ax)
        self.rect.set_edgecolor(original_edgecolor)
        plt.draw()
    def GuardarIMG(self):
        file_path, _ = QFileDialog.getSaveFileName(self.main_window, 'Guardar Imagen', '', 'PNG Files (*.png);;All Files (*)')
        if file_path:
            self.fig.savefig(file_path, bbox_inches='tight', pad_inches=0.1)
    def getNodos(self):
        return self.graph.nodes()
    def getAristas(self):
        return list(self.graph.edges)
    def getPesos(self):
        return nx.get_edge_attributes(self.graph, 'weight')
    def setAristaColor(self,listaAristas,color):
        for tupla in listaAristas:
            nodo1,nodo2=tupla
            self.edge_colors[(nodo1,nodo2)] = color
            self.edge_colors[(nodo2,nodo1)] = color
        self.DibujarGrafo()
    def setAristaColorDirigido(self,listaAristas,color):
        for tupla in listaAristas:
            nodo1,nodo2=tupla
            self.edge_colors[(nodo1,nodo2)] = color
    def Limpiar(self):
        self.graph.clear()
        self.pos = {}
        self.edge_colors.clear()
        self.DibujarGrafo()
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VISUALIZADOR")
        global AltoPanelVista
        global AnchoPanelVista
        AltoPanelVista=600
        AnchoPanelVista=800
        status_bar = self.statusBar()
        self.size_escena = QLabel("")
        status_bar.addWidget(self.size_escena)
        self.setFixedSize(1200,900)
        menubar = self.menuBar()
        menuArchivo = menubar.addMenu("&Archivo")
        menuArchivo.addSeparator()
        menuGrafos = menubar.addMenu("&Grafos")
        menuGrafos.addSeparator()
        menuAlgoritmos = menubar.addMenu("&Algoritmos")
        menuAlgoritmos.addSeparator()
        btnGuardarImagen=QAction('Guardar Imagen', self)
        btnGuardarImagen.triggered.connect(self.GuardarImagen)
        menuArchivo.addAction(btnGuardarImagen)
        btnGrafoPrueba=QAction('Grafo de Prueba', self)
        btnGrafoPrueba.triggered.connect(self.dibujaPruebaGrafo)
        menuGrafos.addAction(btnGrafoPrueba)
        btnselecReco=QAction('Recorrido Seleccionado', self)
        btnselecReco.triggered.connect(self.seleccion)
        menuGrafos.addAction(btnselecReco)
        btnBFS=QAction('BFS-Busqueda en anchura', self)
        btnBFS.triggered.connect(self.BFS)
        menuAlgoritmos.addAction(btnBFS)
        btnKruskal=QAction('Kruskal-Arbol de expansión mínima', self)
        btnKruskal.triggered.connect(self.KRUSKAL)
        menuAlgoritmos.addAction(btnKruskal)
        btnDFS=QAction('DFS-Busqueda en profundidad', self)
        btnDFS.triggered.connect(self.DFS)
        menuAlgoritmos.addAction(btnDFS)
        btnDIJS=QAction('DIJSKTRA-Camino mas corto', self)
        btnDIJS.triggered.connect(self.DIJSKTRA)
        menuAlgoritmos.addAction(btnDIJS)
        global centralWidget 
        centralWidget= PanelVista(AnchoPanelVista, AltoPanelVista)
        self.setCentralWidget(centralWidget)
        self.dock_widget = QDockWidget("Panel de Informacion", self)
        global panel
        panel = Panel()
        panel.setMinimumWidth(300)
        self.dock_widget.setWidget(panel)
        self.dock_widget.setMaximumWidth(300)
        self.dock_widget.setStyleSheet(
                           "QDockWidget::title"
                           "{"
                           "background : lightblue;"
                           "}")
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_widget)
    def GuardarImagen(self):
        centralWidget.GuardarImagen()
    def BFS(self):
        print("BFS ENTRE MAIN")
        print(centralWidget.BFS(1))
    def KRUSKAL(self):
        centralWidget.KRUSKAL()
    def DFS(self):
        centralWidget.DFS(1)
    def DIJSKTRA(self):
        centralWidget.DIJKSTRA(1)
    def dibujaPruebaGrafo(self):
        centralWidget.DibujaPrueba()
    def seleccion(self):
        centralWidget.seleccion_recorrido()
class PanelVista(QWidget):
    def __init__(self,escalaAncho, escalaAlto):
        super().__init__()
        self.ancho = escalaAncho
        self.alto = escalaAlto
        cabezera = QFrame()
        grafoUI = QGroupBox("Vista Grafo")
        cbzAlgoritmo=QGroupBox("Algoritmo")
        lblAlgoritmo = QLabel("Nombre Algoritmo:")
        lblTipo = QLabel("Tipo ALgoritmo:")
        cbzAlgoritmo_layout=QHBoxLayout()
        cbzAlgoritmo_layout.addWidget(lblAlgoritmo)
        cbzAlgoritmo_layout.addWidget(lblTipo)
        cbzAlgoritmo.setLayout(cbzAlgoritmo_layout)
        cbzTipoGrafo=QGroupBox("Selecciona el tipo de grafo")
        self.rbDirigido=QRadioButton("Grafo Dirigido")
        self.rbNoDirigido=QRadioButton("Grafo No Dirigido")
        cbzTipoGrafo_layout=QHBoxLayout()
        cbzTipoGrafo_layout.addWidget(self.rbNoDirigido)
        cbzTipoGrafo_layout.addWidget(self.rbDirigido)
        cbzTipoGrafo.setLayout(cbzTipoGrafo_layout)
        cbzBotones=QGroupBox("Selecciona una opción")
        self.rbDibNodo = QRadioButton('Dibujar Nodo')
        self.rbDibArista = QRadioButton('Dibujar Arista')
        self.btnDibujar = QPushButton('Ingresar Puntos')
        self.btnLimpiar = QPushButton('Limpiar')
        cbzBotones_layout=QHBoxLayout()
        cbzBotones_layout.addWidget(self.rbDibNodo)
        cbzBotones_layout.addWidget(self.rbDibArista)
        cbzBotones_layout.addWidget(self.btnDibujar)
        cbzBotones_layout.addWidget(self.btnLimpiar)
        cbzBotones.setLayout(cbzBotones_layout)
        self.rbDibArista.setObjectName('rbDibArista')
        self.rbDibNodo.setChecked(True)
        self.btnDibujar.setEnabled(False)
        self.rbNoDirigido.setChecked(True)
        cabezera_layout = QVBoxLayout()
        cabezera_layout.addWidget(cbzAlgoritmo)
        cabezera_layout.addWidget(cbzTipoGrafo)
        cabezera_layout.addWidget(cbzBotones)
        cabezera.setLayout(cabezera_layout)
        cabezera.setFixedHeight(290) ### AJUSTA LA PANTALLa
        self.lienzo = Lienzo(self)
        grafoUI_layout = QVBoxLayout()
        grafoUI_layout.addWidget(self.lienzo.fig.canvas)
        grafoUI.setLayout(grafoUI_layout)
        self.setMinimumSize(self.ancho,self.alto)
        main_layout = QVBoxLayout()
        main_layout.addWidget(cabezera)
        main_layout.addWidget(grafoUI)
        self.setLayout(main_layout)
        self.rbDirigido.clicked.connect(self.setTipoGrafo)
        self.rbNoDirigido.clicked.connect(self.setTipoGrafo)
        self.rbDibArista.toggled.connect(lambda state=self.rbDibArista.isChecked(): self.onRadioButtonToggled(state))
        #self.rbNoDirigido.toggled.connect(lambda state = self.rbNoDirigido.isChecked(): self.CambioTipoGrafo(state))
        self.btnDibujar.clicked.connect(self.PideNodos)
        self.btnLimpiar.clicked.connect(self.LimpiarLienzo)
    def setTipoGrafo(self):
        if self.lienzo.graph.number_of_nodes() == 0:
            if(self.rbDirigido.isChecked()):
                self.lienzo.setTipoGrafo("Dirigido")
            elif(self.rbNoDirigido.isChecked()):
                self.lienzo.setTipoGrafo("NoDirigido")
        else:
            if(self.rbDirigido.isChecked()):
                if self.lienzo.Alertas("Cambiando tipo de grafo."):
                    self.lienzo.setTipoGrafo("Dirigido")
                else:
                    self.rbNoDirigido.setChecked(True)
            elif(self.rbNoDirigido.isChecked()):
                if self.lienzo.Alertas("Cambiando tipo de grafo."):
                    self.lienzo.setTipoGrafo("NoDirigido")
                else:
                    self.rbDirigido.setChecked(True)
    def DibujaPrueba(self):
        self.LimpiarLienzo()
        self.lienzo.edge_colors.clear()
        with open("Nodos.txt") as archivo:
            lineas = archivo.readlines()
            for linea in lineas:
                partes = linea.split(", ")
                if len(partes) >= 3:
                    node_id = int(partes[0].strip("()"))
                    posiX = float(partes[1])
                    posiY = float(partes[2].strip(")\n"))
                    self.lienzo.graph.add_node(node_id)
                    self.lienzo.pos[node_id] = (posiX, posiY)
                    self.lienzo.DibujarGrafo()
        with open("Aristas.txt") as aristas:
            lineas = aristas.readlines()
            for linea in lineas:
                partes = linea.split(", ")
                padre = int(partes[0].strip("()"))
                hijo = int(partes[1])
                peso = int(partes[2].strip(")\n"))
                self.lienzo.DibujarArista(padre, hijo, peso)
    def resizeEvent(self, event):
        super().resizeEvent(event)
    def add_node(self, node):    
        node_id = len(self.lienzo.graph.nodes) + 1
        self.lienzo.graph.add_node(node_id)
        self.lienzo.pos[node_id] = (node.x, node.y)
        self.lienzo.DibujarGrafo()
    def onRadioButtonToggled(self, state):
        if state:
            self.lienzo.fig.canvas.mpl_disconnect(self.lienzo.cid)
            self.btnDibujar.setEnabled(True)
        else:
            self.lienzo.fig.canvas.mpl_disconnect(self.lienzo.cid)
            self.lienzo.cid = self.lienzo.fig.canvas.mpl_connect('button_press_event', self.lienzo.MouseClick)
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
                self.lienzo.fig.canvas.mpl_disconnect(self.lienzo.cid)
                self.lienzo.cid = self.lienzo.fig.canvas.mpl_connect('button_press_event', self.lienzo.MouseClick)
    def PideNodos(self):
        dialogo = MiDialogo()
        resultado = dialogo.exec_()
        if resultado == QDialog.Accepted:
            valor1 = dialogo.valor1
            valor2 = dialogo.valor2
            valor3 = dialogo.valor3
            print(self.lienzo.graph.nodes())
            print(self.lienzo.graph.edges())
            if valor1 != None and valor2 != None and valor3 != None:
                self.lienzo.DibujarArista(int(valor1), int(valor2),int(valor3))
            else:
                self.lienzo.Alertas("Ingresar valores correctos")
    def LimpiarLienzo(self):
        self.lienzo.Limpiar()
        global verifica
        verifica = False
    def GuardarImagen(self):
        self.lienzo.GuardarIMG()

    def hayNodos(self):
        return len(self.lienzo.getNodos()) > 0

    def hayAristas(self):
        return len(self.lienzo.getAristas()) > 0
    
    def BFS(self,inicio):
        if self.hayAristas() and self.hayNodos():
            global verifica
            verifica =True
            aristas=[]
            grafo=self.lienzo.getPesos()
            visited = set()  
            queue = deque([(inicio, None)])
            vecinosCargados=set()
            while queue:
                node, prev_node = queue.popleft()
                if node not in visited:
                    visited.add(node)
                if prev_node is not None:
                    tupla=(prev_node,node)
                    print(tupla)
                    aristas.append(tupla)
                neighbors = op.getVecinos(grafo,node)
                for neighbor in neighbors:
                    if neighbor not in visited and neighbor not in vecinosCargados:
                        vecinosCargados.add(neighbor)
                        queue.append((neighbor, node))
            self.lienzo.setAristaColor(aristas,"blue")
        else:
            QMessageBox.warning(self, "Advertencia", "No hay nodo o no hay aristas.")
    def KRUSKAL(self):
        if self.hayAristas() and self.hayNodos():
            global verifica
            verifica =True
            grafo = self.lienzo.getPesos()
            grafoSorted = op.getSortAristas(grafo)
            conjunto_nodos = {nodo: {nodo} for nodo in self.lienzo.getNodos()}
            camino = []
            for arista, peso in grafoSorted:
                nodo1, nodo2 = arista
                conjunto_nodo1 = conjunto_nodos[nodo1]
                conjunto_nodo2 = conjunto_nodos[nodo2]
                if conjunto_nodo1 != conjunto_nodo2:
                    camino.append(arista)
                    self.lienzo.setAristaColor([arista], "blue")
                    nuevo_conjunto = conjunto_nodo1.union(conjunto_nodo2)
                    for nodo in nuevo_conjunto:
                        conjunto_nodos[nodo] = nuevo_conjunto
            self.lienzo.DibujarGrafo()
        else:
            QMessageBox.warning(self, "Advertencia", "No hay nodo o no hay aristas.")
    def DFS(self, inicio):
        if self.hayAristas() and self.hayNodos():
            global verifica
            verifica =True
            def dfs_util(nodo):
                visitado.add(nodo)
                vecinos = list(self.lienzo.graph.neighbors(nodo))
                for veci in vecinos:
                    if veci not in visitado:
                        arista = (nodo, veci)
                        self.lienzo.setAristaColor([arista], "blue")
                        dfs_util(veci)
            visitado = set()
            dfs_util(inicio)
        else:
            QMessageBox.warning(self, "Advertencia", "No hay nodo o no hay aristas.")
    def DIJKSTRA(self, inicio):
        if self.hayAristas() and self.hayNodos():
            global verifica
            verifica =True
            distancias = {node: float('inf') for node in self.lienzo.getNodos()}
            distancias[inicio] = 0
            visitado = set()
            padre = {}
            while len(visitado) != len(distancias):
                min_nodo = None
                min_distancia = float('inf')
                for nodo in distancias:
                    if nodo not in visitado and distancias[nodo] < min_distancia:
                        min_nodo = nodo
                        min_distancia = distancias[nodo]
                visitado.add(min_nodo)
                vecinos = list(self.lienzo.graph.neighbors(min_nodo))
                for veci in vecinos:
                    arista = (min_nodo, veci)
                    peso = self.lienzo.edge_weights.get(arista, 0)
                    if distancias[min_nodo] + peso < distancias[veci]:
                        distancias[veci] = distancias[min_nodo] + peso
                        padre[veci] = min_nodo
            for nodo_destino, nodo_origen in padre.items():
                arista = (nodo_origen, nodo_destino)
                self.lienzo.setAristaColor([arista], "blue")
        else:
            QMessageBox.warning(self, "Advertencia", "No hay nodo o no hay aristas.")
    def seleccion_recorrido(self):
        if self.hayAristas() and self.hayNodos():
                aristas_a_eliminar = []
                aristas_azules = []
                for edge, color in self.lienzo.edge_colors.items():
                    if color == "black":
                        aristas_a_eliminar.append(edge)
                    elif color == "blue":
                        aristas_azules.append(edge)
                for arista in aristas_a_eliminar:
                    nodo1, nodo2 = arista
                    if self.lienzo.graph.has_edge(nodo1, nodo2):
                        self.lienzo.graph.remove_edge(nodo1, nodo2)
                for edge, peso in self.lienzo.edge_weights.items():
                    if edge not in aristas_azules:
                        self.lienzo.edge_colors[edge] = "black"
                self.lienzo.DibujarGrafo()

class Panel(QWidget):
    def __init__(self):
        super().__init__()
app = QApplication([])
window = MainWindow()
window.show()
app.exec_()

