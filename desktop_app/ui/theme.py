def get_dark_theme() -> str:
    return """
    QWidget {
        background-color: #1e1e2e;
        color: #e0e0e0;
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        font-size: 13px;
    }

    QMainWindow {
        background-color: #1e1e2e;
    }

    QTabWidget::pane {
        border: 1px solid #3a3a4c;
        background-color: #1e1e2e;
        border-radius: 4px;
    }

    QTabBar::tab {
        background-color: #2a2a3c;
        color: #a0a0b0;
        padding: 10px 24px;
        border: 1px solid #3a3a4c;
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
        font-weight: bold;
    }

    QTabBar::tab:selected {
        background-color: #1e1e2e;
        color: #e0e0e0;
        border-bottom: 2px solid #7c3aed;
    }

    QTabBar::tab:hover:!selected {
        background-color: #33334a;
    }

    QGroupBox {
        background-color: #2a2a3c;
        border: 1px solid #3a3a4c;
        border-radius: 8px;
        margin-top: 12px;
        padding: 16px;
        padding-top: 28px;
        font-weight: bold;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 4px 12px;
        color: #c0c0d0;
    }

    QLabel {
        background-color: transparent;
        color: #c0c0d0;
    }

    QLineEdit, QSpinBox {
        background-color: #33334a;
        border: 1px solid #3a3a4c;
        border-radius: 6px;
        padding: 8px 12px;
        color: #e0e0e0;
        selection-background-color: #7c3aed;
    }

    QLineEdit:focus, QSpinBox:focus {
        border: 1px solid #7c3aed;
    }

    QComboBox {
        background-color: #33334a;
        border: 1px solid #3a3a4c;
        border-radius: 6px;
        padding: 8px 12px;
        color: #e0e0e0;
        min-width: 100px;
    }

    QComboBox:focus {
        border: 1px solid #7c3aed;
    }

    QComboBox::drop-down {
        border: none;
        width: 24px;
    }

    QComboBox QAbstractItemView {
        background-color: #2a2a3c;
        border: 1px solid #3a3a4c;
        color: #e0e0e0;
        selection-background-color: #7c3aed;
    }

    QPushButton {
        background-color: #7c3aed;
        color: #ffffff;
        border: none;
        border-radius: 6px;
        padding: 10px 20px;
        font-weight: bold;
    }

    QPushButton:hover {
        background-color: #6d28d9;
    }

    QPushButton:pressed {
        background-color: #5b21b6;
    }

    QPushButton:disabled {
        background-color: #3a3a4c;
        color: #666680;
    }

    QPushButton[cssClass="secondary"] {
        background-color: #33334a;
        color: #c0c0d0;
        border: 1px solid #3a3a4c;
    }

    QPushButton[cssClass="secondary"]:hover {
        background-color: #3a3a50;
    }

    QPushButton[cssClass="danger"] {
        background-color: #dc2626;
    }

    QPushButton[cssClass="danger"]:hover {
        background-color: #b91c1c;
    }

    QCheckBox {
        spacing: 8px;
        color: #c0c0d0;
        background-color: transparent;
    }

    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid #3a3a4c;
        background-color: #33334a;
    }

    QCheckBox::indicator:checked {
        background-color: #7c3aed;
        border: 1px solid #7c3aed;
    }

    QPlainTextEdit {
        background-color: #181825;
        border: 1px solid #3a3a4c;
        border-radius: 6px;
        color: #c0d0c0;
        font-family: "SF Mono", "Menlo", "Consolas", monospace;
        font-size: 12px;
        padding: 8px;
    }

    QProgressBar {
        background-color: #33334a;
        border: none;
        border-radius: 8px;
        height: 16px;
        text-align: center;
        color: #e0e0e0;
        font-size: 11px;
    }

    QProgressBar::chunk {
        background-color: #7c3aed;
        border-radius: 8px;
    }

    QScrollArea {
        border: none;
        background-color: transparent;
    }

    QScrollBar:vertical {
        background-color: #1e1e2e;
        width: 10px;
        border-radius: 5px;
    }

    QScrollBar::handle:vertical {
        background-color: #3a3a4c;
        border-radius: 5px;
        min-height: 30px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #4a4a5c;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    QScrollBar:horizontal {
        background-color: #1e1e2e;
        height: 10px;
        border-radius: 5px;
    }

    QScrollBar::handle:horizontal {
        background-color: #3a3a4c;
        border-radius: 5px;
        min-width: 30px;
    }

    QDockWidget {
        titlebar-close-icon: none;
        color: #c0c0d0;
    }

    QDockWidget::title {
        background-color: #2a2a3c;
        padding: 8px;
        border: 1px solid #3a3a4c;
        border-bottom: none;
    }

    QToolBar {
        background-color: #2a2a3c;
        border-bottom: 1px solid #3a3a4c;
        padding: 4px;
        spacing: 4px;
    }
    """
