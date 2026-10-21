import sys
import traceback

from PyQt6.QtWidgets import QApplication, QMessageBox

from ui.main_window import MainWindow


def manejarExcepcionNoCapturada(exc_type, exc_value, exc_tb):
    """Muestra el error en vez de cerrar la app.

    Con el excepthook por defecto, PyQt6 aborta el proceso ante cualquier
    excepción no capturada dentro de un slot.
    """
    traceback.print_exception(exc_type, exc_value, exc_tb)
    if QApplication.instance() is None:
        return
    QMessageBox.critical(
        None,
        "Error inesperado",
        f"Ocurrió un error y la operación no se completó:\n\n{exc_type.__name__}: {exc_value}",
    )


def main():
    sys.excepthook = manejarExcepcionNoCapturada
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
