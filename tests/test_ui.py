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
from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from core.graph_service import GraphService
from ui.dialogs import DialogoArista
from ui.main_window import MainWindow

APP = QApplication.instance() or QApplication(sys.argv)


def evento(x, y, button=1, key=None, px=(0, 0)):
    return SimpleNamespace(xdata=x, ydata=y, button=button, key=key, x=px[0], y=px[1], step=1)


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

        self.panel = self.window.centralWidget
        self.lienzo = self.panel.lienzo

        self.alertas = []
        self.confirmar = True
        self.lienzo.Alertas = lambda msg, titulo="": self.alertas.append(msg)
        self.lienzo.alertaConfirmacion = lambda msg: self.confirmar
        # Por defecto se descartan cambios pendientes sin preguntar (los tests
        # de PersistenciaTests usan el método real).
        self.window.confirmarCambiosPendientes = lambda: True

        self.window.dibujaPruebaGrafo()
        self.modo_seleccion()

    def tearDown(self):
        self.assertEqual(self.errores, [], "Hubo excepciones no capturadas")

    def modo_seleccion(self):
        # Con 'Dibujar Arista' activo, el clic selecciona en vez de crear nodos.
        self.panel.btnDibujar.setEnabled(True)

    def modo_dibujar_nodo(self):
        self.panel.btnDibujar.setEnabled(False)

    def clic_en_nodo(self, nodo, **kwargs):
        self.lienzo.MouseClick(evento(*self.lienzo.pos[nodo], **kwargs))


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
        self.assertTrue(self.panel.rbNoDirigido.isChecked())
        self.assertEqual(self.lienzo.model.graph_type, "Undirected")


class SeleccionTests(UiTestCase):
    def test_clic_selecciona_arista(self):
        p1, p2 = self.lienzo.pos[1], self.lienzo.pos[8]
        self.lienzo.MouseClick(evento((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2))

        self.assertEqual(set(self.lienzo.selected_edge), {1, 8})

    def test_editar_peso_de_arista_seleccionada(self):
        self.lienzo.selected_edge = (1, 8)

        def aceptar(dialogo):
            dialogo.entrada3.setText("42")
            dialogo.Guardar()
            return QDialog.DialogCode.Accepted

        with mock.patch.object(DialogoArista, "exec", aceptar):
            self.panel.editarPesoArista()

        self.assertEqual(self.lienzo.graph[1][8]["weight"], 42)

    def test_eliminar_seleccion_multiple(self):
        self.clic_en_nodo(2, key="control")
        self.clic_en_nodo(3, key="control")

        self.window.handleSelectionDelete()

        self.assertNotIn(2, self.lienzo.graph)
        self.assertNotIn(3, self.lienzo.graph)

    def test_borrar_nodo_seleccionado_limpia_seleccion(self):
        self.clic_en_nodo(4)
        self.assertEqual(self.lienzo.selected_node, 4)

        self.clic_en_nodo(4, button=3)
        self.window.handleSelectionEdit()

        self.assertIsNone(self.lienzo.selected_node)


class VistaTests(UiTestCase):
    def test_toolbar_en_modo_zoom_no_crea_nodos(self):
        self.modo_dibujar_nodo()
        antes = self.lienzo.graph.number_of_nodes()

        self.panel.toolbar.zoom()
        self.lienzo.MouseClick(evento(0.5, 0.05))
        self.panel.toolbar.zoom()
        self.assertEqual(self.lienzo.graph.number_of_nodes(), antes)

        self.lienzo.MouseClick(evento(0.5, 0.05))
        self.assertEqual(self.lienzo.graph.number_of_nodes(), antes + 1)

    def test_redibujar_conserva_zoom_externo(self):
        self.lienzo.ax.set_xlim(0.2, 0.6)
        self.lienzo.DibujarGrafo()

        self.assertEqual([round(v, 3) for v in self.lienzo.ax.get_xlim()], [0.2, 0.6])

    def test_pan_usa_pixeles(self):
        self.lienzo.MouseClick(evento(0.5, 0.5, button=2, px=(100, 100)))
        self.lienzo.MouseMove(evento(0.5, 0.5, px=(150, 100)))
        primero = self.lienzo.ax.get_xlim()
        self.lienzo.MouseMove(evento(0.4, 0.5, px=(150, 100)))

        self.assertEqual(self.lienzo.ax.get_xlim(), primero)
        self.assertLess(primero[0], 0)

    def test_filtro_actualiza_panel(self):
        self.lienzo.setVisualFilter('hide_isolated')

        self.assertIn("Sin aislados", self.window.panel.view_label.text())


class TipoGrafoTests(UiTestCase):
    def test_reclic_en_radio_actual_no_borra(self):
        self.panel.rbNoDirigido.click()

        self.assertEqual(self.lienzo.graph.number_of_nodes(), 8)

    def test_cancelar_cambio_revierte_radio(self):
        self.confirmar = False
        self.panel.rbDirigido.click()

        self.assertTrue(self.panel.rbNoDirigido.isChecked())
        self.assertEqual(self.lienzo.model.graph_type, "Undirected")
        self.assertEqual(self.lienzo.graph.number_of_nodes(), 8)

    def test_aceptar_cambio_a_dirigido(self):
        self.panel.rbDirigido.click()

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
        self.clic_en_nodo(1)
        self.lienzo.MouseMove(evento(0.9, 0.9))
        self.lienzo.MouseRelease(evento(0.9, 0.9))
        self.assertEqual(self.lienzo.pos[1], (0.9, 0.9))

        self.lienzo.Deshacer()

        self.assertEqual(self.lienzo.pos[1], original)

    def test_clic_sin_mover_no_registra_historial(self):
        self.clic_en_nodo(1)
        self.lienzo.MouseRelease(evento(0, 0))

        self.assertFalse(self.lienzo.history.can_undo)

    def test_deshacer_cambio_de_tipo_restaura_radio(self):
        self.panel.rbDirigido.click()
        self.lienzo.Deshacer()

        self.assertEqual(self.lienzo.model.graph_type, "Undirected")
        self.assertTrue(self.panel.rbNoDirigido.isChecked())
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
        self.window.solicitarInicio = lambda: 1
        self.window.ejecutarBFS()
        self.assertTrue(self.lienzo.edge_colors)

        self.lienzo.eliminarArista(1, 2)

        self.assertEqual(self.lienzo.edge_colors, {})
        self.assertEqual(self.panel.lblTipo.text(), "")


class AlgoritmosUiTests(UiTestCase):
    def test_dfs_desde_menu(self):
        self.window.solicitarInicio = lambda: 1
        self.window.ejecutarDFS()

        self.assertIn("Pasos DFS", self.window.panel.content_label.text())

    def test_centralidad_resalta_top_5(self):
        self.window.ejecutarCentralidad()

        self.assertEqual(len(self.lienzo.analysis_highlighted_nodes), 5)


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
        self.window.solicitarInicio = lambda: 1
        self.window.ejecutarBFS()
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
    def test_guardar_imagen(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = str(Path(tmp) / "grafo.png")
            with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(destino, "")):
                self.lienzo.GuardarIMG()

            self.assertTrue(Path(destino).stat().st_size > 0)


if __name__ == "__main__":
    unittest.main()
