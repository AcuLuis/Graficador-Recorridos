"""Pruebas de la interfaz sin ventana visible (Qt en modo offscreen)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog

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


class AlgoritmosUiTests(UiTestCase):
    def test_dfs_desde_menu(self):
        self.window.solicitarInicio = lambda: 1
        self.window.ejecutarDFS()

        self.assertIn("Pasos DFS", self.window.panel.content_label.text())

    def test_centralidad_resalta_top_5(self):
        self.window.ejecutarCentralidad()

        self.assertEqual(len(self.lienzo.analysis_highlighted_nodes), 5)


class ExportarTests(UiTestCase):
    def test_guardar_imagen(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = str(Path(tmp) / "grafo.png")
            with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(destino, "")):
                self.lienzo.GuardarIMG()

            self.assertTrue(Path(destino).stat().st_size > 0)


if __name__ == "__main__":
    unittest.main()
