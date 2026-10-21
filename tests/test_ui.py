"""Pruebas de la interfaz sin ventana visible (Qt en modo offscreen)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox

from core.graph_service import GraphService
from ui.canvas import MODO_ARISTA, MODO_NODO, MODO_SELECCIONAR
from ui.main_window import MainWindow

APP = QApplication.instance() or QApplication(sys.argv)


class UiTestCase(unittest.TestCase):
    def setUp(self):
        self.errores = []
        hook_original = sys.excepthook
        sys.excepthook = lambda t, v, tb: self.errores.append(f"{t.__name__}: {v}")
        self.addCleanup(setattr, sys, "excepthook", hook_original)

        self.window = MainWindow()
        self.window.resize(1200, 800)
        self.window.show()
        APP.processEvents()
        self.addCleanup(self.window.close)
        # Se ejecuta antes del cierre (orden LIFO): vacía redibujados pendientes
        # para que no se disparen sobre una ventana ya destruida.
        self.addCleanup(APP.processEvents)

        self.lienzo = self.window.lienzo

        self.alertas = []
        self.confirmar = True
        self.lienzo.Alertas = lambda msg, titulo="": self.alertas.append(msg)
        self.lienzo.alertaConfirmacion = lambda msg: self.confirmar
        # Por defecto se descartan cambios pendientes sin preguntar (los tests
        # de PersistenciaTests usan el método real).
        self.window.confirmarCambiosPendientes = lambda: True

        self.menus = []
        self.window._ejecutarMenu = self.menus.append

        self.window.dibujaPruebaGrafo()

    def tearDown(self):
        self.assertEqual(self.errores, [], "Hubo excepciones no capturadas")

    # Utilidades

    def evento(self, x, y, button=1, key=None, dblclick=False, px=None):
        if px is None:
            px = self.lienzo.ax.transData.transform((x, y))
        return SimpleNamespace(
            xdata=x, ydata=y, button=button, key=key, dblclick=dblclick, x=px[0], y=px[1], step=1
        )

    def clic(self, x, y, **kwargs):
        evento = self.evento(x, y, **kwargs)
        self.lienzo.MouseClick(evento)
        self.lienzo.MouseRelease(evento)

    def clic_en_nodo(self, nodo, **kwargs):
        self.clic(*self.lienzo.pos[nodo], **kwargs)

    def punto_medio(self, u, v):
        (x1, y1), (x2, y2) = self.lienzo.pos[u], self.lienzo.pos[v]
        return (x1 + x2) / 2, (y1 + y2) / 2

    def accion_de_menu(self, menu, texto):
        for accion in menu.actions():
            if accion.menu() is not None:
                encontrada = self.accion_de_menu(accion.menu(), texto)
                if encontrada is not None:
                    return encontrada
            elif texto in accion.text():
                return accion
        return None

    def resaltadas(self):
        return {edge for edge, color in self.lienzo.edge_colors.items() if color == "blue"}


class CargaTests(UiTestCase):
    def test_grafo_de_prueba_carga_desde_otro_directorio(self):
        cwd = os.getcwd()
        os.chdir(tempfile.gettempdir())
        self.addCleanup(os.chdir, cwd)

        self.lienzo.Limpiar()
        self.window.dibujaPruebaGrafo()

        self.assertEqual(self.lienzo.graph.number_of_nodes(), 8)

    def test_json_corrupto_muestra_alerta(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
            tmp.write("{ roto")
        self.addCleanup(os.remove, tmp.name)

        self.assertFalse(self.lienzo.cargarJson(tmp.name))
        self.assertTrue(self.alertas)
        self.assertEqual(self.lienzo.graph.number_of_nodes(), 8)

    def test_cargar_sincroniza_tipo_de_grafo(self):
        self.assertEqual(self.window.comboTipo.currentIndex(), 0)
        self.assertEqual(self.lienzo.model.graph_type, "Undirected")


class ModosTests(UiTestCase):
    def test_modo_nodo_crea_nodo_en_espacio_vacio(self):
        self.window.setModo(MODO_NODO)

        self.clic(0.5, 0.05)

        self.assertIn(9, self.lienzo.graph)
        self.assertIn("Nodo 9 creado", self.window.statusBar().currentMessage())

    def test_modo_nodo_no_crea_encima_de_otro_nodo(self):
        self.window.setModo(MODO_NODO)

        self.clic_en_nodo(1)

        self.assertEqual(self.lienzo.graph.number_of_nodes(), 8)
        self.assertEqual(self.lienzo.selected_node, 1)

    def test_modo_seleccionar_no_crea_nodos(self):
        self.clic(0.5, 0.05)

        self.assertEqual(self.lienzo.graph.number_of_nodes(), 8)

    def test_modo_arista_con_dos_clics(self):
        self.window.setModo(MODO_ARISTA)

        self.clic_en_nodo(7)
        self.assertEqual(self.lienzo.origen_arista, 7)
        with mock.patch.object(QInputDialog, "getInt", return_value=(4, True)) as pedir:
            self.clic_en_nodo(6)

        pedir.assert_called_once()
        self.assertEqual(self.lienzo.graph[7][6]["weight"], 4)
        self.assertIsNone(self.lienzo.origen_arista)

    def test_modo_arista_cancelar_peso_no_crea(self):
        self.window.setModo(MODO_ARISTA)
        self.clic_en_nodo(7)
        with mock.patch.object(QInputDialog, "getInt", return_value=(1, False)):
            self.clic_en_nodo(6)

        self.assertFalse(self.lienzo.graph.has_edge(7, 6))

    def test_esc_cancela_arista_pendiente(self):
        self.window.setModo(MODO_ARISTA)
        self.clic_en_nodo(7)

        self.window.actCancelar.trigger()

        self.assertIsNone(self.lienzo.origen_arista)

    def test_esc_sin_accion_pendiente_limpia_seleccion(self):
        self.clic_en_nodo(1)

        self.window.actCancelar.trigger()

        self.assertIsNone(self.lienzo.selected_node)

    def test_cambiar_de_modo_cancela_arista_pendiente(self):
        self.window.setModo(MODO_ARISTA)
        self.clic_en_nodo(7)

        self.window.actModos[MODO_SELECCIONAR].trigger()

        self.assertIsNone(self.lienzo.origen_arista)
        self.assertEqual(self.lienzo.modo, MODO_SELECCIONAR)


class SeleccionTests(UiTestCase):
    def test_clic_selecciona_arista(self):
        self.clic(*self.punto_medio(1, 8))

        self.assertEqual(set(self.lienzo.selected_edge), {1, 8})

    def test_clic_elige_el_nodo_mas_cercano(self):
        self.lienzo.moverNodo(2, (0.50, 0.50))
        self.lienzo.moverNodo(3, (0.52, 0.50))

        self.clic(0.519, 0.50)

        self.assertEqual(self.lienzo.selected_node, 3)

    def test_tolerancia_en_pixeles_no_depende_del_zoom(self):
        x, y = self.lienzo.pos[1]
        for _ in range(10):
            self.lienzo.zoomOut()

        # A 0.04 en datos el nodo queda dentro del radio cuando la vista está alejada.
        self.clic(x + 0.04, y)
        self.assertEqual(self.lienzo.selected_node, 1)

        self.lienzo.resetView()
        for _ in range(10):
            self.lienzo.zoomIn()
        self.lienzo.current_xlim = [x - 0.1, x + 0.1]
        self.lienzo.current_ylim = [y - 0.1, y + 0.1]
        self.clic(x + 0.04, y)
        self.assertIsNone(self.lienzo.selected_node)

    def test_nodos_ocultos_no_se_pueden_seleccionar(self):
        self.lienzo.moverNodo(1, (0.9, 0.05))
        for vecino in list(self.lienzo.graph.neighbors(1)):
            self.lienzo.eliminarArista(1, vecino)
        self.window.aplicarFiltro('hide_isolated')

        self.clic_en_nodo(1)

        self.assertIsNone(self.lienzo.selected_node)

    def test_clic_en_fondo_deselecciona(self):
        self.clic_en_nodo(1)

        self.clic(0.5, 0.02)

        self.assertIsNone(self.lienzo.selected_node)

    def test_arrastrar_fondo_desplaza_vista_sin_deseleccionar(self):
        self.clic_en_nodo(1)
        inicio = self.evento(0.5, 0.02)
        self.lienzo.MouseClick(inicio)
        self.lienzo.MouseMove(self.evento(0.5, 0.02, px=(inicio.x + 80, inicio.y)))
        self.lienzo.MouseRelease(self.evento(0.5, 0.02))

        self.assertLess(self.lienzo.ax.get_xlim()[0], 0)
        self.assertEqual(self.lienzo.selected_node, 1)

    def test_doble_clic_en_arista_edita_peso(self):
        with mock.patch.object(QInputDialog, "getInt", return_value=(42, True)):
            self.clic(*self.punto_medio(1, 8), dblclick=True)

        self.assertEqual(self.lienzo.graph[1][8]["weight"], 42)

    def test_editar_peso_de_arista_seleccionada(self):
        self.clic(*self.punto_medio(1, 8))
        with mock.patch.object(QInputDialog, "getInt", return_value=(42, True)):
            self.window.actEditar.trigger()

        self.assertEqual(self.lienzo.graph[1][8]["weight"], 42)

    def test_eliminar_seleccion_multiple(self):
        self.clic_en_nodo(2, key="control")
        self.clic_en_nodo(3, key="control")

        self.window.actEliminar.trigger()

        self.assertNotIn(2, self.lienzo.graph)
        self.assertNotIn(3, self.lienzo.graph)

    def test_acciones_de_seleccion_deshabilitadas_sin_seleccion(self):
        self.assertFalse(self.window.actEliminar.isEnabled())

        self.clic_en_nodo(1)

        self.assertTrue(self.window.actEliminar.isEnabled())


class MenuContextualTests(UiTestCase):
    def test_menu_de_nodo_selecciona_y_ofrece_acciones(self):
        self.clic_en_nodo(4, button=3)

        self.assertEqual(self.lienzo.selected_node, 4)
        menu = self.menus[-1]
        self.assertIsNotNone(self.accion_de_menu(menu, "Eliminar nodo"))
        self.assertIsNotNone(self.accion_de_menu(menu, "BFS"))

    def test_eliminar_nodo_desde_menu(self):
        self.clic_en_nodo(4, button=3)

        self.accion_de_menu(self.menus[-1], "Eliminar nodo").trigger()

        self.assertNotIn(4, self.lienzo.graph)
        self.assertIsNone(self.lienzo.selected_node)

    def test_ejecutar_bfs_desde_nodo(self):
        self.clic_en_nodo(5, button=3)

        self.accion_de_menu(self.menus[-1], "BFS").trigger()

        self.assertIn("Visita nodo 5 (nivel 0)", self.window.panel.content_label.text())

    def test_menu_de_arista(self):
        self.clic(*self.punto_medio(1, 8), button=3)

        with mock.patch.object(QInputDialog, "getInt", return_value=(7, True)):
            self.accion_de_menu(self.menus[-1], "Editar peso").trigger()

        self.assertEqual(self.lienzo.graph[1][8]["weight"], 7)

    def test_menu_de_fondo_agrega_nodo(self):
        self.clic(0.5, 0.02, button=3)

        self.accion_de_menu(self.menus[-1], "Agregar nodo aquí").trigger()

        self.assertIn(9, self.lienzo.graph)
        self.assertEqual(self.lienzo.pos[9], (0.5, 0.02))


class VistaTests(UiTestCase):
    def test_redibujar_conserva_zoom(self):
        self.lienzo.ax.set_xlim(0.2, 0.6)
        self.lienzo.DibujarGrafo()

        self.assertEqual([round(v, 3) for v in self.lienzo.ax.get_xlim()], [0.2, 0.6])

    def test_pan_con_boton_central_usa_pixeles(self):
        self.lienzo.MouseClick(self.evento(0.5, 0.5, button=2, px=(100, 100)))
        self.lienzo.MouseMove(self.evento(0.5, 0.5, px=(150, 100)))
        primero = self.lienzo.ax.get_xlim()
        self.lienzo.MouseMove(self.evento(0.4, 0.5, px=(150, 100)))

        self.assertEqual(self.lienzo.ax.get_xlim(), primero)
        self.assertLess(primero[0], 0)

    def test_ajustar_vista_encuadra_nodos(self):
        self.lienzo.current_xlim = [5, 6]
        self.window.actAjustarVista.trigger()

        x0, x1 = self.lienzo.ax.get_xlim()
        for x, _ in self.lienzo.pos.values():
            self.assertTrue(x0 < x < x1)

    def test_filtro_actualiza_panel_y_menu(self):
        self.window.actFiltros['hide_isolated'].trigger()

        self.assertIn("Sin aislados", self.window.panel.view_label.text())
        self.assertTrue(self.window.actFiltros['hide_isolated'].isChecked())

    def test_filtro_de_componente_requiere_seleccion(self):
        self.window.actFiltros['component'].trigger()

        self.assertTrue(self.alertas)
        self.assertTrue(self.window.actFiltros['all'].isChecked())

    def test_panel_lateral_se_puede_reabrir(self):
        accion = self.window.dock_widget.toggleViewAction()
        accion.trigger()
        self.assertFalse(self.window.dock_widget.isVisible())

        accion.trigger()
        self.assertTrue(self.window.dock_widget.isVisible())


class TipoGrafoTests(UiTestCase):
    def elegir(self, indice, decision):
        self.window._preguntarCambioTipo = lambda tipo: decision
        self.window.comboTipo.setCurrentIndex(indice)

    def test_cancelar_cambio_revierte_selector(self):
        self.elegir(1, None)

        self.assertEqual(self.window.comboTipo.currentIndex(), 0)
        self.assertEqual(self.lienzo.model.graph_type, "Undirected")
        self.assertEqual(self.lienzo.graph.number_of_nodes(), 8)

    def test_convertir_conserva_el_grafo(self):
        self.elegir(1, 'convertir')

        self.assertEqual(self.lienzo.model.graph_type, "Directed")
        self.assertEqual(self.lienzo.graph.number_of_nodes(), 8)
        self.assertEqual(self.lienzo.graph.number_of_edges(), 17)

    def test_empezar_vacio(self):
        self.elegir(1, 'vaciar')

        self.assertEqual(self.lienzo.model.graph_type, "Directed")
        self.assertEqual(self.lienzo.graph.number_of_nodes(), 0)

    def test_grafo_vacio_cambia_sin_preguntar(self):
        self.window.nuevoGrafo()
        self.window._preguntarCambioTipo = mock.Mock()

        self.window.comboTipo.setCurrentIndex(1)

        self.window._preguntarCambioTipo.assert_not_called()
        self.assertEqual(self.lienzo.model.graph_type, "Directed")


class HistorialTests(UiTestCase):
    def test_deshacer_y_rehacer_eliminar_nodo(self):
        self.lienzo.eliminarNodo(1)
        self.assertNotIn(1, self.lienzo.graph)

        self.lienzo.Deshacer()
        self.assertIn(1, self.lienzo.graph)
        self.assertEqual(self.lienzo.graph[1][2]["weight"], 10)

        self.lienzo.Rehacer()
        self.assertNotIn(1, self.lienzo.graph)

    def test_deshacer_reemplazo_de_peso_restaura_peso(self):
        self.lienzo.DibujarArista(1, 2, 99)
        self.assertEqual(self.lienzo.graph[1][2]["weight"], 99)

        self.lienzo.Deshacer()

        self.assertTrue(self.lienzo.graph.has_edge(1, 2))
        self.assertEqual(self.lienzo.graph[1][2]["weight"], 10)

    def test_deshacer_limpiar(self):
        self.lienzo.Limpiar()
        self.lienzo.Deshacer()

        self.assertEqual(self.lienzo.graph.number_of_nodes(), 8)

    def test_deshacer_arrastre(self):
        original = self.lienzo.pos[1]
        self.lienzo.MouseClick(self.evento(*original))
        self.lienzo.MouseMove(self.evento(0.9, 0.9))
        self.lienzo.MouseRelease(self.evento(0.9, 0.9))
        self.assertEqual(self.lienzo.pos[1], (0.9, 0.9))

        self.lienzo.Deshacer()

        self.assertEqual(self.lienzo.pos[1], original)

    def test_clic_sin_mover_no_registra_historial(self):
        self.clic_en_nodo(1)

        self.assertFalse(self.lienzo.history.can_undo)

    def test_deshacer_cambio_de_tipo_restaura_selector(self):
        self.window._preguntarCambioTipo = lambda tipo: 'vaciar'
        self.window.comboTipo.setCurrentIndex(1)

        self.lienzo.Deshacer()

        self.assertEqual(self.lienzo.model.graph_type, "Undirected")
        self.assertEqual(self.window.comboTipo.currentIndex(), 0)
        self.assertEqual(self.lienzo.graph.number_of_nodes(), 8)

    def test_eliminar_seleccion_es_un_solo_paso(self):
        self.clic_en_nodo(2, key="control")
        self.clic_en_nodo(3, key="control")
        self.window.handleSelectionDelete()

        self.lienzo.Deshacer()

        self.assertIn(2, self.lienzo.graph)
        self.assertIn(3, self.lienzo.graph)
        self.assertFalse(self.lienzo.history.can_undo)

    def test_acciones_de_menu_reflejan_historial(self):
        self.assertFalse(self.window.actDeshacer.isEnabled())

        self.lienzo.eliminarNodo(1)

        self.assertTrue(self.window.actDeshacer.isEnabled())
        self.assertFalse(self.window.actRehacer.isEnabled())


class ValidacionAristasTests(UiTestCase):
    def test_rechaza_lazo(self):
        self.lienzo.DibujarArista(1, 1, 3)

        self.assertFalse(self.lienzo.graph.has_edge(1, 1))
        self.assertTrue(self.alertas)

    def test_no_reemplaza_si_se_cancela(self):
        self.confirmar = False
        self.lienzo.DibujarArista(1, 2, 99)

        self.assertEqual(self.lienzo.graph[1][2]["weight"], 10)
        self.assertFalse(self.lienzo.history.can_undo)

    def test_editar_grafo_descarta_resultado_de_algoritmo(self):
        self.window.ejecutarBFS(inicio=1)
        self.assertTrue(self.lienzo.edge_colors)

        self.lienzo.eliminarArista(1, 2)

        self.assertEqual(self.lienzo.edge_colors, {})
        self.assertFalse(self.window.panel.algorithm_label.isVisible())


class AlgoritmosUiTests(UiTestCase):
    def test_dfs_desde_menu(self):
        self.window.solicitarInicio = lambda: 1
        self.window.ejecutarDFS()

        self.assertIn("Pasos DFS", self.window.panel.content_label.text())
        self.assertEqual(self.window.panel.algorithm_label.text(), "DFS - Profundidad")

    def test_centralidad_resalta_top_5(self):
        self.window.ejecutarCentralidad()

        self.assertEqual(len(self.lienzo.analysis_highlighted_nodes), 5)

    def test_dijkstra_con_destino_resalta_solo_el_camino(self):
        self.window.solicitarDestino = lambda: (True, 6)

        self.window.ejecutarDijkstra(inicio=1)

        # 1 -> 3 -> 6 (6 + 4 = 10) es el más corto.
        self.assertEqual(self.resaltadas(), {(1, 3), (3, 1), (3, 6), (6, 3)})
        self.assertIn("costo 10", self.window.panel.content_label.text())

    def test_error_del_algoritmo_se_muestra_como_aviso(self):
        with mock.patch.object(QMessageBox, "warning") as aviso:
            self.window.ejecutarBFS(inicio=99)

        aviso.assert_called_once()
        self.assertIn("no existe", aviso.call_args.args[2])

    def test_nuevo_resultado_reemplaza_colores_anteriores(self):
        self.window.ejecutarBFS(inicio=1)
        self.window.solicitarDestino = lambda: (True, 2)
        self.window.ejecutarDijkstra(inicio=1)

        # 1 -> 3 -> 2 (6 + 3 = 9) es más corto que la arista directa 1 - 2 (10).
        self.assertEqual(self.resaltadas(), {(1, 3), (3, 1), (3, 2), (2, 3)})

    def test_todas_las_acciones_del_menu_funcionan(self):
        self.window.solicitarInicio = lambda: 1
        self.window.solicitarDestino = lambda: (True, None)
        menu = next(a.menu() for a in self.window.menuBar().actions() if "Algoritmos" in a.text())

        for tipo in ("Undirected", "Directed"):
            self.lienzo.model.set_graph_type(tipo)
            for grupo in menu.actions():
                for accion in grupo.menu().actions():
                    with self.subTest(tipo=tipo, accion=accion.text()), \
                            mock.patch.object(QMessageBox, "warning"):
                        accion.trigger()


class PersistenciaTests(UiTestCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.destino = str(Path(self.tmp.name) / "mi_grafo.json")

    def confirmar_real(self, boton):
        with mock.patch.object(QMessageBox, "question", return_value=boton):
            return MainWindow.confirmarCambiosPendientes(self.window)

    def guardar_como(self, destino):
        with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(destino, "")):
            return self.window.guardarGrafo()

    def test_grafo_de_prueba_no_queda_asociado_a_su_archivo(self):
        self.assertIsNone(self.lienzo.ruta_actual)
        self.assertFalse(self.lienzo.hay_cambios)
        self.assertIn("datos_prueba", self.window.windowTitle())

    def test_guardar_sin_ruta_pide_destino_y_lo_recuerda(self):
        self.assertTrue(self.guardar_como(self.destino))

        self.assertEqual(self.lienzo.ruta_actual, self.destino)
        self.assertFalse(self.window.isWindowModified())
        self.assertIn("mi_grafo.json", self.window.windowTitle())

        self.lienzo.eliminarNodo(1)
        with mock.patch.object(QFileDialog, "getSaveFileName") as dialogo:
            self.window.guardarGrafo()
        dialogo.assert_not_called()
        self.assertNotIn(1, GraphService.load_json(self.destino).graph)

    def test_guardar_como_agrega_extension(self):
        self.guardar_como(str(Path(self.tmp.name) / "sin_extension"))

        self.assertTrue(self.lienzo.ruta_actual.endswith("sin_extension.json"))

    def test_edicion_marca_cambios_y_deshacer_los_quita(self):
        self.lienzo.eliminarNodo(1)
        self.assertTrue(self.window.isWindowModified())

        self.lienzo.Deshacer()
        self.assertFalse(self.window.isWindowModified())

    def test_json_guardado_no_incluye_colores_de_algoritmo(self):
        self.window.ejecutarBFS(inicio=1)
        self.assertFalse(self.lienzo.hay_cambios)

        self.guardar_como(self.destino)

        datos = json.loads(Path(self.destino).read_text(encoding="utf-8"))
        self.assertNotIn("edge_colors", datos)

    def test_confirmar_sin_cambios_no_pregunta(self):
        with mock.patch.object(QMessageBox, "question") as pregunta:
            self.assertTrue(MainWindow.confirmarCambiosPendientes(self.window))
        pregunta.assert_not_called()

    def test_confirmar_cancelar_detiene_la_accion(self):
        self.lienzo.eliminarNodo(1)

        self.assertFalse(self.confirmar_real(QMessageBox.StandardButton.Cancel))

    def test_confirmar_descartar_permite_continuar(self):
        self.lienzo.eliminarNodo(1)

        self.assertTrue(self.confirmar_real(QMessageBox.StandardButton.Discard))

    def test_confirmar_guardar_guarda(self):
        self.lienzo.eliminarNodo(1)
        with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(self.destino, "")):
            self.assertTrue(self.confirmar_real(QMessageBox.StandardButton.Save))

        self.assertTrue(Path(self.destino).exists())
        self.assertFalse(self.lienzo.hay_cambios)

    def test_cerrar_con_cambios_y_cancelar_no_cierra(self):
        self.window.confirmarCambiosPendientes = lambda: False
        evento_cierre = QCloseEvent()

        self.window.closeEvent(evento_cierre)

        self.assertFalse(evento_cierre.isAccepted())
        self.window.confirmarCambiosPendientes = lambda: True

    def test_nuevo_grafo(self):
        self.window.nuevoGrafo()

        self.assertEqual(self.lienzo.graph.number_of_nodes(), 0)
        self.assertIn("Sin título", self.window.windowTitle())
        self.assertFalse(self.lienzo.history.can_undo)


class ExportarTests(UiTestCase):
    def test_exportar_imagen(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = str(Path(tmp) / "grafo.png")
            with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(destino, "")):
                self.window.exportarImagen()

            self.assertTrue(Path(destino).stat().st_size > 0)


if __name__ == "__main__":
    unittest.main()
