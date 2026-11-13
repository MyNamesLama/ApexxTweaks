"""Small original stroke icons; no font, CDN or downloaded assets required."""

from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

PATHS = {
    "dashboard": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    "optimization": '<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3"/><circle cx="16" cy="17" r="3"/>',
    "gaming": '<path d="M7 7h10c3 0 5 8 4 11-1 3-5-1-6-2H9c-1 1-5 5-6 2C2 15 4 7 7 7Z"/><path d="M8 10v5M5.5 12.5h5M16 11h.1M18 14h.1"/>',
    "monitor": '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4M4 11h4l2-4 4 7 2-3h4"/>',
    "benchmarks": '<path d="M4 3v17h17M8 16l4-6 4 2 5-7"/>',
    "restore": '<path d="M3 10a9 9 0 1 1 1 8M3 4v6h6M12 7v5l3 2"/>',
    "settings": '<path d="m9 3-1 3-3 1-2 3 2 2-1 3 2 3h3l2 3h3l1-3 3-1 2-3-2-2 1-3-2-3h-3l-2-3Z"/><circle cx="12" cy="12" r="3"/>',
    "arrow": '<path d="M4 12h15M13 6l6 6-6 6"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "cpu": '<rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
    "shield": '<path d="m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6Z"/><path d="m8 12 3 3 5-6"/>',
    "logo": '<path d="M3 20 11 3h3l7 17h-5l-4-10-4 10ZM9 17h6"/>',
}


def icon(name, color="#aab2a6", size=20):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{PATHS.get(name, PATHS["dashboard"])}</svg>'
    pix = QPixmap(size * 2, size * 2)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    pix.setDevicePixelRatio(2)
    return QIcon(pix)
