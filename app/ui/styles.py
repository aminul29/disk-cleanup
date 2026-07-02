from __future__ import annotations

from PySide6.QtWidgets import QApplication


def apply_app_style(app: QApplication, theme: str = "System") -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(_dark_style() if theme == "Dark" else _light_style())


def _light_style() -> str:
    return """
    * {
        outline: none;
    }
    QWidget {
        background: #f6f8fc;
        color: #18202c;
        font-family: "Segoe UI";
        font-size: 13px;
    }
    QLabel {
        background: transparent;
    }
    QWidget#Root {
        background: #f6f8fc;
    }
    QStackedWidget#ContentStack {
        background: #f6f8fc;
        border: none;
    }
    QScrollArea {
        background: transparent;
        border: none;
    }
    QScrollArea > QWidget > QWidget {
        background: transparent;
    }
    QDialog {
        background: #f6f8fc;
        color: #18202c;
    }
    QFrame#Sidebar {
        background: #0b1220;
        border: none;
    }
    QLabel#AppTitle {
        color: white;
        font-size: 22px;
        font-weight: 700;
        letter-spacing: 0;
        padding: 4px 0 2px 0;
    }
    QLabel#AppSubtitle {
        color: #93a4bb;
        font-size: 12px;
    }
    QLabel#MutedText {
        color: #64748b;
    }
    QLabel#SectionTitle {
        color: #08111f;
        font-size: 17px;
        font-weight: 800;
    }
    QLabel#SectionDescription {
        color: #64748b;
        line-height: 145%;
    }
    QLabel#InfoPill {
        color: #1e4fbf;
        background: #eaf1ff;
        border: 1px solid #d6e4ff;
        border-radius: 10px;
        padding: 9px 11px;
        font-weight: 700;
    }
    QLabel#SidebarPlan {
        color: #e2e8f0;
        background: #172033;
        border: 1px solid #26344d;
        border-radius: 10px;
        padding: 12px;
        font-weight: 600;
    }
    QListWidget {
        background: transparent;
        border: none;
        color: #cbd5e1;
        outline: none;
        padding: 2px 0;
    }
    QListWidget::item {
        border-radius: 10px;
        margin: 3px 8px;
        padding: 12px 14px;
    }
    QListWidget::item:hover {
        background: #172033;
        color: white;
    }
    QListWidget::item:selected {
        background: #2f6df6;
        color: white;
    }
    QScrollBar:vertical, QScrollBar:horizontal {
        background: transparent;
        width: 0;
        height: 0;
    }
    QFrame[class="Card"] {
        background: white;
        border: 1px solid #dfe5ef;
        border-radius: 14px;
    }
    QLabel[class="CardTitle"] {
        font-size: 13px;
        color: #52627a;
        font-weight: 700;
        text-transform: uppercase;
    }
    QLabel[class="CardValue"] {
        color: #08111f;
        font-size: 30px;
        font-weight: 800;
    }
    QLabel[class="HeroValue"] {
        color: #08111f;
        font-size: 34px;
        font-weight: 800;
    }
    QPushButton {
        background: #2f6df6;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 11px 16px;
        font-weight: 700;
    }
    QPushButton:hover {
        background: #255bd6;
    }
    QPushButton:disabled {
        background: #a9b4c4;
    }
    QPushButton[class="Secondary"] {
        background: #e9eefb;
        color: #1e4fbf;
    }
    QPushButton[class="Secondary"]:hover {
        background: #dfe7f8;
    }
    QPushButton[class="Danger"] {
        background: #dc2626;
    }
    QPushButton[class="Danger"]:hover {
        background: #b91c1c;
    }
    QTableWidget, QTreeWidget, QTextEdit, QListWidget#SettingsList {
        background: white;
        alternate-background-color: #f8fafc;
        border: 1px solid #dfe5ef;
        border-radius: 12px;
        gridline-color: #eef2f7;
        selection-background-color: #dbe8ff;
        selection-color: #0f172a;
    }
    QTableWidget::item, QTreeWidget::item {
        padding: 6px;
    }
    QTreeWidget::item {
        min-height: 28px;
    }
    QListWidget#SettingsList {
        padding: 8px;
    }
    QListWidget#SettingsList::item {
        color: #334155;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 9px;
        margin: 4px;
        padding: 10px;
    }
    QListWidget#SettingsList::item:selected {
        color: #0f172a;
        background: #dbe8ff;
        border-color: #b7cdfa;
    }
    QHeaderView::section {
        background: #f7f9fc;
        border: none;
        border-bottom: 1px solid #dfe5ef;
        padding: 9px;
        font-weight: 700;
        color: #475569;
    }
    QLineEdit, QComboBox {
        background: white;
        border: 1px solid #cfd8e6;
        border-radius: 10px;
        padding: 9px;
        min-height: 20px;
    }
    QComboBox::drop-down {
        border: none;
        width: 28px;
    }
    QCheckBox {
        background: transparent;
        color: #172033;
        spacing: 10px;
        padding: 8px 0;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 1px solid #b8c4d6;
        background: white;
    }
    QCheckBox::indicator:hover {
        border-color: #2f6df6;
    }
    QCheckBox::indicator:checked {
        background: #2f6df6;
        border-color: #2f6df6;
    }
    QDialogButtonBox QPushButton {
        min-width: 120px;
    }
    QProgressBar {
        background: #e7edf6;
        border: none;
        border-radius: 7px;
        height: 14px;
    }
    QProgressBar::chunk {
        background: #2f6df6;
        border-radius: 7px;
    }
    """


def _dark_style() -> str:
    return _light_style() + """
    QWidget {
        background: #0f172a;
        color: #e5e7eb;
    }
    QDialog {
        background: #0f172a;
        color: #e5e7eb;
    }
    QWidget#Root, QStackedWidget#ContentStack, QScrollArea {
        background: #0f172a;
    }
    QFrame[class="Card"], QTableWidget, QTreeWidget, QTextEdit, QListWidget#SettingsList, QLineEdit, QComboBox {
        background: #111827;
        color: #e5e7eb;
        border-color: #374151;
    }
    QLabel#MutedText, QLabel[class="CardTitle"], QLabel#SectionDescription {
        color: #9ca3af;
    }
    QLabel#SectionTitle {
        color: #f8fafc;
    }
    QLabel#InfoPill {
        color: #bfdbfe;
        background: #172554;
        border-color: #1d4ed8;
    }
    QLabel[class="CardValue"], QLabel[class="HeroValue"] {
        color: #f8fafc;
    }
    QHeaderView::section {
        background: #1f2937;
        color: #e5e7eb;
        border-bottom-color: #374151;
    }
    QCheckBox {
        color: #e5e7eb;
    }
    QCheckBox::indicator {
        background: #0f172a;
        border-color: #475569;
    }
    """
