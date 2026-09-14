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

centralWidget = None
panel = None
ancho = None
altura = None
posX = None
posY = None


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
        self.ax.axis('off')  # Desactivar ejes
        self.rect = plt.Rectangle((0,0), 1, 1, linewidth=2, edgecolor='black', facecolor='none')
        self.ax.add_patch(self.rect)

    def DibujarArista(self, posNodo1, posNodo2,peso=1):
        #with open("Aristas.txt", 'a') as archivo:
        #   archivo.write(f"({posNodo1}, {posNodo2}, {peso})\n")
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
        alerta.setText("Elemento no encontrado")
        alerta.setInformativeText(mensaje)
        alerta.setWindowTitle("Alerta")
        alerta.exec_()

    def MouseClick(self, event):
        #print("Click")
        if event.xdata is not None and event.ydata is not None:
            if self.main_window.dibNodoIsSelected():
                node_id = len(self.graph.nodes) + 1
                self.graph.add_node(node_id)
                self.pos[node_id] = (event.xdata, event.ydata)
                #with open("Nodos.txt", 'a') as archivo:
                #    archivo.write(f"({node_id}, {event.xdata}, {event.ydata})\n")
                if self.main_window.dibNodoIsSelected():
                    self.DibujarGrafo()

    def DibujarGrafo(self):
        # Obtener los pesos de las aristas y guardarlos en un diccionario
        edge_labels = nx.get_edge_attributes(self.graph, 'weight')

        # Guardar temporalmente el color del borde del rectángulo
        original_edgecolor = self.rect.get_edgecolor()
        self.ax.clear()
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.axis('off')  # Desactivar ejes
        self.rect = plt.Rectangle((0, 0), 1, 1, linewidth=2, edgecolor='black', facecolor='none')

        self.ax.add_patch(self.rect)
        
        # Dibujar el grafo después de restaurar el color del borde
        if( not self.edge_colors and not self.edge_weights):
             nx.draw(self.graph, pos=self.pos, with_labels=True, font_weight='bold', ax=self.ax)
             nx.draw_networkx_edge_labels(self.graph, pos=self.pos, edge_labels=edge_labels, ax=self.ax)
        else:
            nx.draw(self.graph, pos=self.pos, with_labels=True, font_weight='bold', ax=self.ax,
                edge_color=[self.edge_colors.get(edge, 'black') for edge in self.graph.edges()])
            #width=[self.edge_weights.get(edge, 1) for edge in self.graph.edges()]
            nx.draw_networkx_edge_labels(self.graph, pos=self.pos, edge_labels=edge_labels, ax=self.ax)

        # Restaurar el color del borde original
        self.rect.set_edgecolor(original_edgecolor)
        plt.draw()
    #GUARDAR IMAGEN
    def GuardarIMG(self):
        #Poner la ruta
        file_path, _ = QFileDialog.getSaveFileName(self.main_window, 'Guardar Imagen', '', 'PNG Files (*.png);;All Files (*)')

        if file_path:
            # Guarda la imagen como PNG
            self.fig.savefig(file_path, bbox_inches='tight', pad_inches=0.1)


    def getNodos(self):
        return self.graph.nodes()
    
    def getAristas(self):
        return list(self.graph.edges)
    def getPesos(self):
        return nx.get_edge_attributes(self.graph, 'weight')
    #Cambia el color de las aristas que estan en la lista, función para colorear el camino
    def setAristaColor(self,listaAristas,color):
        for tupla in listaAristas:
            nodo1,nodo2=tupla
            self.edge_colors[(nodo1,nodo2)] = color
            self.edge_colors[(nodo2,nodo1)] = color
    

        self.DibujarGrafo()
        #tupla: NodoPadre,NodoHijo
    def Limpiar(self):
        self.graph.clear()
        self.pos = {}
        self.DibujarGrafo()
    

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VISUALIZADOR")

        global AltoPanelVista
        global AnchoPanelVista
        AltoPanelVista=600
        AnchoPanelVista=800
        # Crear una barra de estado
        status_bar = self.statusBar()

        # Agregar un mensaje a la barra de estado
        self.size_escena = QLabel("")
        status_bar.addWidget(self.size_escena)
     
        #pantalla = QDesktopWidget().screenGeometry()
        #self.setGeometry(pantalla.x(), pantalla.y()+20, pantalla.width(), pantalla.height())
        self.setFixedSize(1200,900)
        # self.screen()
        menubar = self.menuBar()

        #MENUS
        menuArchivo = menubar.addMenu("&Archivo")
        menuArchivo.addSeparator()
        menuGrafos = menubar.addMenu("&Grafos")
        menuGrafos.addSeparator()
        menuAlgoritmos = menubar.addMenu("&Algoritmos")
        menuAlgoritmos.addSeparator()
        
        #SUBMENUS para Menu Archivo
        btnGuardarImagen=QAction('Guardar Imagen', self)
        btnGuardarImagen.triggered.connect(self.GuardarImagen)
        menuArchivo.addAction(btnGuardarImagen)

        #SUBMENUS para Grafos
        btnGrafoPrueba=QAction('Grafo de Prueba', self)
        btnGrafoPrueba.triggered.connect(self.dibujaPruebaGrafo)
        menuGrafos.addAction(btnGrafoPrueba)
        #SUBMENUS ALGORITMOS
        #BFS
        btnBFS=QAction('BFS-Busqueda en anchura', self)
        btnBFS.triggered.connect(self.BFS)
        menuAlgoritmos.addAction(btnBFS)
        
        btnKruskal=QAction('Kruskal-Arbol de expansión mínima', self)
        btnKruskal.triggered.connect(self.KRUSKAL)
        menuAlgoritmos.addAction(btnKruskal)


        # ESCENA DE INICIO POR DEFECTO
        ##global centralWidget
        global centralWidget 
        centralWidget= PanelVista(AnchoPanelVista, AltoPanelVista)
        self.setCentralWidget(centralWidget)
        
        #PANEL DE INFORMACIÓN
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

    #Otras Funciones
    def GuardarImagen(self):
        centralWidget.GuardarImagen()

    #Funciones para ejecutar los algoritmos
    def BFS(self):
        print("BFS ENTRE MAIN")
        print(centralWidget.BFS(1))
    def KRUSKAL(self):
        centralWidget.KRUSKAL()
    def dibujaPruebaGrafo(self):
        centralWidget.DibujaPrueba()
    
class PanelVista(QWidget):
    def __init__(self,escalaAncho, escalaAlto):
        super().__init__()
        self.ancho = escalaAncho
        self.alto = escalaAlto
        # Crear cabezera y GrafoUI
        cabezera = QFrame()
        grafoUI = QGroupBox("Vista Grafo")

        #Crear seccion detalle algoritmo
        cbzAlgoritmo=QGroupBox("Algoritmo")
        lblAlgoritmo = QLabel("Nombre Algoritmo:")
        lblTipo = QLabel("Tipo ALgoritmo:")
        cbzAlgoritmo_layout=QHBoxLayout()
        cbzAlgoritmo_layout.addWidget(lblAlgoritmo)
        cbzAlgoritmo_layout.addWidget(lblTipo)
        cbzAlgoritmo.setLayout(cbzAlgoritmo_layout)

        #Crear sección botones
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
        
        # Asignar un nombre específico a cada radio button
        self.rbDibArista.setObjectName('rbDibArista')

        # Establecer por defecto la selección del radiobutton 'Dibujar Nodo'
        self.rbDibNodo.setChecked(True)
        self.btnDibujar.setEnabled(False)
        
        # Configurar contenido para la cabezera
        cabezera_layout = QVBoxLayout()
        cabezera_layout.addWidget(cbzAlgoritmo)
        cabezera_layout.addWidget(cbzBotones)
        cabezera.setLayout(cabezera_layout)
        # Configurar dimensiones de cabezera
        cabezera.setFixedHeight(200)

        # Configurar contenido para grafoUI
        
        self.lienzo = Lienzo(self)
        grafoUI_layout = QVBoxLayout()
        grafoUI_layout.addWidget(self.lienzo.fig.canvas)
        grafoUI.setLayout(grafoUI_layout)

        # Configuración general del widget
        self.setMinimumSize(self.ancho,self.alto)

        # Diseño principal con los dos frames
        main_layout = QVBoxLayout()
        main_layout.addWidget(cabezera)
        main_layout.addWidget(grafoUI)
        self.setLayout(main_layout)

         # Conectar la función onRadioButtonToggled al evento toggled de rbDibArista
        self.rbDibArista.toggled.connect(lambda state=self.rbDibArista.isChecked(): self.onRadioButtonToggled(state))
        self.btnDibujar.clicked.connect(self.PideNodos)
        self.btnLimpiar.clicked.connect(self.LimpiarLienzo)
        
    
    def DibujaPrueba(self):
        self.LimpiarLienzo()

        with open("Nodos.txt") as archivo:
            lineas = archivo.readlines()
            for linea in lineas:
                partes = linea.split(", ")
                if len(partes) >= 3:
                    # Obtener el id, la posición x y la posición y
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
            self.btnDibujar.setEnabled(True)
        else:
            # Restaurar la función MouseClick al evento 'button_press_event'
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
                # Restore the original MouseClick behavior
                self.lienzo.fig.canvas.mpl_disconnect(self.lienzo.cid)
                self.lienzo.cid = self.lienzo.fig.canvas.mpl_connect('button_press_event', self.lienzo.MouseClick)

    def PideNodos(self):
        dialogo = MiDialogo()
        resultado = dialogo.exec_()
        if resultado == QDialog.Accepted:
            valor1 = dialogo.valor1
            valor2 = dialogo.valor2
            valor3 = dialogo.valor3
            print(self.lienzo.graph.nodes()) # Para ver los Nodos
            print(self.lienzo.graph.edges())

            if valor1 != None and valor2 != None and valor3 != None:
                self.lienzo.DibujarArista(int(valor1), int(valor2),int(valor3))
            else:
                self.lienzo.Alertas("Ingresar valores correctos")

    def LimpiarLienzo(self):
        self.lienzo.Limpiar()
    def GuardarImagen(self):
        self.lienzo.GuardarIMG()

    #Algoritmos de busquedad
    def BFS(self,inicio):
        aristas=[]
        grafo=self.lienzo.getPesos()
        visited = set()  # Conjunto para almacenar nodos visitados
        queue = deque([(inicio, None)])  # Cola para la búsqueda en anchura (incluye la arista anterior)
        vecinosCargados=set()
        while queue:
            node, prev_node = queue.popleft()  # Sacar el primer nodo de la cola
            if node not in visited:
                visited.add(node)  # Marcar el nodo como visitado
            # Dibujar arista si no es el primer nodo
            if prev_node is not None:
                tupla=(prev_node,node)
                print(tupla)
                aristas.append(tupla)
            # Obtener vecinos del nodo actual y sus pesos
            neighbors = op.getVecinos(grafo,node)
            # Agregar nodos vecinos no visitados a la cola junto con la información de la arista
            
            for neighbor in neighbors:
                if neighbor not in visited and neighbor not in vecinosCargados:
                    vecinosCargados.add(neighbor)
                    queue.append((neighbor, node))

        self.lienzo.setAristaColor(aristas,"blue")
    def KRUSKAL(self):
        grafo=self.lienzo.getPesos()
        grafoSorted= op.getSortAristas(grafo)
        visitados=set()
        camino=[]
        cola=deque()
        for arista,peso in grafoSorted:
            cola.append((arista))
        while cola:
            nodo1, nodo2 = cola.popleft() 
            if(nodo1 not in visitados or nodo2 not in visitados):
                if(nodo1 not in visitados ):
                    visitados.add(nodo1)
                if(nodo2 not in visitados ):
                    visitados.add(nodo2)  
                    tuplaArista=(nodo1 , nodo2)
                    print(tuplaArista)
                    camino.append(tuplaArista)

        self.lienzo.setAristaColor(camino,"blue")
class Panel(QWidget):
    def __init__(self):
        super().__init__()
        

 

   

app = QApplication([])
window = MainWindow()
window.show()
app.exec_()


