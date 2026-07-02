from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("class", "Card")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(15, 23, 42, 24))
        self.setGraphicsEffect(shadow)


class StatCard(Card):
    def __init__(self, title: str, value: str = "-", detail: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(138)
        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "CardTitle")
        self.value_label = QLabel(value)
        self.value_label.setProperty("class", "CardValue")
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
        f"background: {background}; color: {color}; border-radius: 8px; padding: 4px 8px; font-weight: 700;"
    )
    return label


def page_header(title: str, subtitle: str) -> QWidget:
    wrapper = QWidget()
    wrapper.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
    layout = QVBoxLayout(wrapper)
    layout.setContentsMargins(0, 0, 0, 16)
    layout.setSpacing(5)
    title_label = QLabel(title)
    title_label.setStyleSheet("font-size: 30px; font-weight: 800; color: #08111f;")
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
