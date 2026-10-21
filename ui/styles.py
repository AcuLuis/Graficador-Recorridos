APP_STYLESHEET = """
* { font-family: 'Segoe UI', 'Arial', sans-serif; }

QMainWindow, QDialog, QWidget {
    background-color: #edf2f7;
    color: #1f2937;
}

/* ── Barra de menú ── */
QMenuBar {
    background-color: #1a1a2e;
    color: #e8e8e8;
    padding: 3px 2px;
    font-size: 13px;
}
QMenuBar::item {
    background: transparent;
    padding: 6px 12px;
    border-radius: 5px;
}
QMenuBar::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4aa5df, stop:1 #2c8dd8);
    color: white;
}
QMenu {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #d4d9e0;
    border-radius: 8px;
    padding: 4px 0;
}
QMenu::item {
    padding: 6px 24px;
}
QMenu::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4aa5df, stop:1 #2c8dd8);
    color: white;
    border-radius: 4px;
}

/* ── Paneles y agrupaciones ── */
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #d1dae4;
    border-radius: 10px;
    margin-top: 12px;
    padding: 18px 12px 10px 12px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:1 #f8fafc);
    color: #1f2937;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 2px 8px;
    color: #334155;
    background-color: #f8fafc;
    border-radius: 4px;
}

/* ── Radio buttons ── */
QRadioButton {
    color: #1f2937;
    font-size: 13px;
    font-weight: bold;
    spacing: 6px;
    padding: 4px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #94a3b8;
    border-radius: 10px;
    background-color: #ffffff;
}
QRadioButton::indicator:checked {
    background-color: #3ea5e8;
    border-color: #2f8fce;
}

/* ── Botones ── */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #49afd9, stop:1 #2a8fcc);
    color: white;
    border: 1px solid #247db7;
    padding: 8px 16px;
    border-radius: 8px;
    font-weight: bold;
    font-size: 13px;
    min-height: 32px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #58b9e6, stop:1 #2682c0);
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #227bb0, stop:1 #1d6b9a);
}
QPushButton:disabled {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #d5dde6, stop:1 #c5cfdb);
    border-color: #b7c1ce;
    color: #7a8897;
}

/* ── Campos de texto ── */
QLineEdit {
    background-color: #ffffff;
    color: #1f2937;
    border: 2px solid #cbd5e1;
    border-radius: 7px;
    padding: 6px 10px;
    font-size: 13px;
}
QLineEdit:focus {
    border: 2px solid #3498db;
}

/* ── Panel lateral (dock) ── */
QDockWidget {
    color: #ffffff;
    font-size: 13px;
}
QDockWidget::title {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #1f2a3a, stop:1 #152238);
    color: white;
    padding: 8px 12px;
    font-weight: bold;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QDockWidget::close-button, QDockWidget::float-button {
    background: transparent;
    border: none;
    padding: 2px;
}

/* ── ScrollArea y contenido ── */
QScrollArea {
    border: none;
    background-color: #f8fafc;
}
QScrollArea > QWidget > QWidget {
    background-color: #f8fafc;
}

/* ── Labels ── */
QLabel {
    color: #1f2937;
    font-size: 13px;
}

/* ── MessageBox y diálogos ── */
QMessageBox {
    background-color: #ffffff;
}
QMessageBox QLabel {
    color: #1f2937;
    font-size: 13px;
}
/* ── Barra de herramientas ── */
QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #d1dae4;
    padding: 4px 6px;
    spacing: 4px;
}
QToolBar::separator {
    background-color: #d1dae4;
    width: 1px;
    margin: 4px 6px;
}
QToolButton {
    color: #1f2937;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 13px;
    font-weight: bold;
}
QToolButton:hover {
    background-color: #e8f2fb;
    border-color: #b6d7f0;
}
QToolButton:checked {
    background-color: #2a8fcc;
    border-color: #247db7;
    color: white;
}
QToolButton:disabled {
    color: #a0aab5;
}
QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 4px 10px;
    min-width: 110px;
}

/* ── Lienzo y barra de estado ── */
QFrame#contenedorLienzo {
    background-color: #edf2f7;
}
QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #d1dae4;
    color: #334155;
}
QStatusBar QLabel {
    color: #475569;
    padding: 0 8px;
}
"""
