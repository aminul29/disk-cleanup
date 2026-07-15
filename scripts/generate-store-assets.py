from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ICON = ROOT / "app" / "assets" / "app-icon.svg"
APP_ASSETS = ROOT / "app" / "assets"
MSIX_ASSETS = ROOT / "packaging" / "msix" / "Assets"


def render_icon(output: Path, width: int, height: int, icon_size: int | None = None) -> None:
    renderer = QSvgRenderer(QByteArray(SOURCE_ICON.read_bytes()))
    if not renderer.isValid():
        raise RuntimeError(f"Could not render {SOURCE_ICON}")

    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor("#0b1220"))
    painter = QPainter(image)
    size = icon_size or min(width, height)
    left = (width - size) / 2
    top = (height - size) / 2
    renderer.render(painter, QRectF(left, top, size, size))
    painter.end()

    output.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(output)):
        raise RuntimeError(f"Could not save {output}")


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    _ = app

    square_assets = {
        "StoreLogo.png": 50,
        "Square44x44Logo.png": 44,
        "Square71x71Logo.png": 71,
        "Square150x150Logo.png": 150,
        "Square310x310Logo.png": 310,
        "StoreListingLogo.png": 300,
    }
    for name, size in square_assets.items():
        render_icon(MSIX_ASSETS / name, size, size)
    render_icon(MSIX_ASSETS / "Wide310x150Logo.png", 310, 150, 118)
    render_icon(APP_ASSETS / "app-icon.ico", 256, 256)
    print(f"Generated Windows assets in {MSIX_ASSETS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
