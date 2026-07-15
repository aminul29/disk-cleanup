from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("class", "Card")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(15, 23, 42, 18))
        self.setGraphicsEffect(shadow)


class StatCard(Card):
    def __init__(self, title: str, value: str = "-", detail: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(124)
        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "CardTitle")
        self.value_label = QLabel(value)
        self.value_label.setProperty("class", "CardValue")
        self.value_label.setWordWrap(True)
        self.detail_label = QLabel(detail)
        self.detail_label.setObjectName("MutedText")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(9)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.detail_label)

    def set_values(self, value: str, detail: str = "") -> None:
        self.value_label.setText(value)
        self.detail_label.setText(detail)


class SegmentedControl(QFrame):
    value_changed = Signal(str)

    def __init__(self, options: list[str], current: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SegmentedControl")
        self.buttons: dict[str, QPushButton] = {}
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        for option in options:
            button = QPushButton(option)
            button.setCheckable(True)
            button.setProperty("class", "SegmentButton")
            button.setMinimumWidth(110)
            self.group.addButton(button)
            self.buttons[option] = button
            layout.addWidget(button)
            button.clicked.connect(lambda checked, value=option: self._emit_value(value, checked))
        self.set_value(current)

    def value(self) -> str:
        checked = self.group.checkedButton()
        return checked.text() if checked is not None else ""

    def set_value(self, value: str) -> None:
        button = self.buttons.get(value)
        if button is not None:
            button.setChecked(True)

    def _emit_value(self, value: str, checked: bool) -> None:
        if checked:
            self.value_changed.emit(value)


def risk_badge(text: str) -> QLabel:
    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    colors = {
        "Safe": ("#dcfce7", "#166534"),
        "Review": ("#fef3c7", "#92400e"),
        "Protected": ("#e5e7eb", "#374151"),
    }
    background, color = colors.get(text, ("#e5e7eb", "#374151"))
    label.setStyleSheet(
        f"background: {background}; color: {color}; border-radius: 5px; "
        "padding: 4px 8px; font-weight: 700;"
    )
    return label


def page_header(title: str, subtitle: str) -> QWidget:
    wrapper = QWidget()
    wrapper.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
    layout = QVBoxLayout(wrapper)
    layout.setContentsMargins(0, 0, 0, 16)
    layout.setSpacing(5)
    title_label = QLabel(title)
    title_label.setObjectName("PageTitle")
    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("MutedText")
    layout.addWidget(title_label)
    layout.addWidget(subtitle_label)
    return wrapper


def horizontal_row(*widgets: QWidget) -> QWidget:
    wrapper = QWidget()
    layout = QHBoxLayout(wrapper)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    for widget in widgets:
        layout.addWidget(widget)
    return wrapper
