from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


def apply_app_style(app: QApplication, theme: str = "System") -> None:
    app.setStyle("Fusion")
    system_dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    use_dark = theme == "Dark" or (theme == "System" and system_dark)
    app.setStyleSheet(_dark_style() if use_dark else _light_style())


def _light_style() -> str:
    return """
    * {
        outline: none;
    }
    QWidget {
        background: #f4f6fa;
        color: #18202c;
        font-family: "Segoe UI";
        font-size: 14px;
    }
    QLabel {
        background: transparent;
    }
    QWidget#Root {
        background: #f4f6fa;
    }
    QStackedWidget#ContentStack {
        background: #f4f6fa;
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
        background: #f4f6fa;
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
    QLabel#PageTitle {
        color: #08111f;
        font-size: 28px;
        font-weight: 800;
    }
    QLabel#OnboardingTitle {
        color: #08111f;
        font-size: 26px;
        font-weight: 800;
    }
    QLabel#FeatureTitle {
        color: #172033;
        font-size: 15px;
        font-weight: 700;
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
        border-radius: 6px;
        padding: 9px 11px;
        font-weight: 700;
    }
    QLabel#EmptyState {
        color: #52627a;
        background: #f8fafc;
        border: 1px dashed #cbd5e1;
        border-radius: 8px;
        padding: 20px;
        font-weight: 600;
    }
    QLabel#SidebarPlan {
        color: #e2e8f0;
        background: #172033;
        border: 1px solid #26344d;
        border-radius: 8px;
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
        border-radius: 7px;
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
    QScrollBar:vertical {
        background: transparent;
        width: 10px;
        margin: 2px;
    }
    QScrollBar::handle:vertical {
        background: #cbd5e1;
        border-radius: 4px;
        min-height: 32px;
    }
    QScrollBar:horizontal {
        background: transparent;
        height: 10px;
        margin: 2px;
    }
    QScrollBar::handle:horizontal {
        background: #cbd5e1;
        border-radius: 4px;
        min-width: 32px;
    }
    QScrollBar::add-line, QScrollBar::sub-line {
        width: 0;
        height: 0;
    }
    QFrame[class="Card"] {
        background: white;
        border: 1px solid #dfe5ef;
        border-radius: 8px;
    }
    QFrame[class="OnboardingRow"] {
        background: white;
        border: 1px solid #dfe5ef;
        border-radius: 8px;
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
    QLabel[class="CardValueCompact"] {
        color: #08111f;
        font-size: 24px;
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
        border-radius: 7px;
        padding: 11px 16px;
        font-weight: 700;
        min-height: 20px;
    }
    QPushButton:hover {
        background: #255bd6;
    }
    QPushButton:disabled {
        background: #a9b4c4;
        color: #eef2f7;
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
        border-radius: 8px;
        gridline-color: #eef2f7;
        selection-background-color: #dbe8ff;
        selection-color: #0f172a;
    }
    QTextEdit#AdvisorText {
        background: transparent;
        border: none;
        padding: 0;
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
        border-radius: 6px;
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
        border-radius: 7px;
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
    QFrame#SegmentedControl {
        background: #e9eef6;
        border: 1px solid #d8e0eb;
        border-radius: 8px;
    }
    QPushButton[class="SegmentButton"] {
        background: transparent;
        color: #52627a;
        border-radius: 6px;
        padding: 7px 14px;
        min-height: 18px;
    }
    QPushButton[class="SegmentButton"]:checked {
        background: white;
        color: #1748ad;
        border: 1px solid #cfd8e6;
    }
    QTabWidget::pane {
        border: 1px solid #dfe5ef;
        border-radius: 8px;
        background: white;
        top: -1px;
    }
    QTabBar::tab {
        background: transparent;
        color: #64748b;
        padding: 10px 16px;
        border-bottom: 2px solid transparent;
    }
    QTabBar::tab:selected {
        color: #1748ad;
        border-bottom-color: #2f6df6;
        font-weight: 700;
    }
    QToolTip {
        color: white;
        background: #172033;
        border: 1px solid #26344d;
        padding: 6px;
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
        background: transparent;
        color: #e5e7eb;
    }
    QLabel {
        background: transparent;
    }
    QDialog {
        background: #111318;
        color: #e5e7eb;
    }
    QWidget#Root, QStackedWidget#ContentStack, QScrollArea {
        background: #111318;
    }
    QFrame#Sidebar {
        background: #0b0d11;
    }
    QLabel#SidebarPlan {
        background: #1a1e25;
        border-color: #303641;
    }
    QPushButton {
        background: #2f6df6;
        color: white;
    }
    QPushButton:hover {
        background: #3b78ff;
    }
    QPushButton:disabled {
        background: #2a2f38;
        color: #737d8c;
    }
    QPushButton[class="Secondary"] {
        background: #222730;
        color: #bfdbfe;
        border: 1px solid #353d49;
    }
    QPushButton[class="Secondary"]:hover {
        background: #2b313c;
        border-color: #465161;
    }
    QPushButton[class="Secondary"]:disabled {
        background: #1b1e24;
        color: #626b78;
        border-color: #2c313a;
    }
    QPushButton[class="Danger"] {
        background: #dc2626;
        color: white;
    }
    QFrame[class="Card"], QTableWidget, QTreeWidget, QTextEdit, QListWidget#SettingsList, QLineEdit, QComboBox {
        background: #181b21;
        color: #e5e7eb;
        border-color: #343a45;
    }
    QTableWidget, QTreeWidget, QTextEdit, QListWidget#SettingsList {
        alternate-background-color: #15181d;
        selection-background-color: #28456f;
        selection-color: #f8fafc;
    }
    QListWidget#SettingsList::item {
        color: #d6dbe3;
        background: #20242b;
        border-color: #343a45;
    }
    QListWidget#SettingsList::item:selected {
        color: #f8fafc;
        background: #28456f;
        border-color: #3e67a3;
    }
    QLabel#EmptyState {
        color: #a7b0be;
        background: #15181d;
        border-color: #3b424e;
    }
    QLabel#MutedText, QLabel[class="CardTitle"], QLabel#SectionDescription {
        color: #9ca3af;
    }
    QLabel#SectionTitle {
        color: #f8fafc;
    }
    QLabel#PageTitle {
        color: #f8fafc;
    }
    QLabel#OnboardingTitle, QLabel#FeatureTitle {
        color: #f8fafc;
    }
    QLabel#InfoPill {
        color: #bfdbfe;
        background: #18263d;
        border-color: #2e5ca8;
    }
    QLabel[class="CardValue"], QLabel[class="CardValueCompact"], QLabel[class="HeroValue"] {
        color: #f8fafc;
    }
    QHeaderView::section {
        background: #20242b;
        color: #e5e7eb;
        border-bottom-color: #343a45;
    }
    QCheckBox {
        color: #e5e7eb;
    }
    QCheckBox::indicator {
        background: #111318;
        border-color: #475569;
    }
    QFrame#SegmentedControl {
        background: #22262d;
        border-color: #343a45;
    }
    QPushButton[class="SegmentButton"] {
        color: #9ca3af;
    }
    QPushButton[class="SegmentButton"]:checked {
        background: #181b21;
        color: #bfdbfe;
        border-color: #475569;
    }
    QTabWidget::pane {
        background: #181b21;
        border-color: #343a45;
    }
    QFrame[class="OnboardingRow"] {
        background: #181b21;
        border-color: #343a45;
    }
    """
