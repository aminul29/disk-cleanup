from __future__ import annotations

from functools import lru_cache

from lucide import lucide_icon as lucide_svg
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


@lru_cache(maxsize=128)
def icon(name: str, color: str = "#334155", size: int = 20) -> QIcon:
    svg = lucide_svg(
        name,
        width=str(size),
        height=str(size),
        stroke=color,
        stroke_width="2",
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)
