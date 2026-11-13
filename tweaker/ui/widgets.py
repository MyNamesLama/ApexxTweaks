"""Reusable cards, accessible switches and cheap-on-idle painted plots."""

import math
from PySide6.QtCore import Qt, QRectF, QSize, QRect, QPoint
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QPushButton,
    QSizePolicy,
    QAbstractButton,
    QWidget,
    QScrollArea,
    QLayout,
)
from .theme import ACCENT, MUTED


def label(text="", role="", wrap=True):
    w = QLabel(text)
    w.setTextFormat(Qt.TextFormat.PlainText)
    if role:
        w.setObjectName(role)
    w.setWordWrap(wrap and role not in ("tag", "limeTag", "eyebrow"))
    w.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return w


def button(text, callback, primary=False, danger=False):
    w = QPushButton(text.replace("&", "&&"))
    w.setAccessibleName(text)
    w.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        w.setObjectName("primary")
    elif danger:
        w.setObjectName("danger")
    w.clicked.connect(callback)
    return w


class Card(QFrame):
    def __init__(self, parent=None, hero=False):
        super().__init__(parent)
        self.setObjectName("hero" if hero else "card")
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(20, 18, 20, 18)
        self.box.setSpacing(12)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)


class MetricCard(Card):
    def __init__(self, title, value="Unavailable", detail="Not inspected"):
        super().__init__()
        self.box.addWidget(label(title, "caption"))
        self.value = label(value, "metric")
        self.box.addWidget(self.value)
        self.detail = label(detail, "muted")
        self.box.addWidget(self.detail)

    def set(self, value, detail):
        self.value.setText(value)
        self.detail.setText(detail)


class Switch(QAbstractButton):
    """Keyboard-operable button: Space toggles, accessible name supplied by caller."""

    def __init__(self, name, checked=False):
        super().__init__()
        self.setCheckable(True)
        self.setChecked(checked)
        self.setAccessibleName(name)
        self.setToolTip(name)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(44, 26)

    def sizeHint(self):
        return QSize(44, 26)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = ACCENT if self.isChecked() and self.isEnabled() else "#414b3a"
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(bg))
        p.drawRoundedRect(QRectF(1, 3, 42, 22), 11, 11)
        p.setBrush(QColor("#16200d" if self.isChecked() else "#c2ccba"))
        p.drawEllipse(QRectF(24 if self.isChecked() else 4, 6, 16, 16))
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(ACCENT), 1))
            p.drawRoundedRect(QRectF(0.5, 0.5, 43, 25), 5, 5)


class Chart(QWidget):
    def __init__(self, title="Usage", unit="%", limit=100):
        super().__init__()
        self.title = title
        self.unit = unit
        self.limit = limit
        self.values = []
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setAccessibleName(title + " chart")

    def set_values(self, values):
        self.values = [
            float(v) for v in values if v is not None and math.isfinite(float(v))
        ][-90:]
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = QRectF(40, 18, max(10, self.width() - 54), max(10, self.height() - 43))
        maximum = self.limit or max(self.values or [1]) * 1.1 or 1
        p.setPen(QColor("#30392a"))
        for fraction in (0, 0.5, 1):
            y = bounds.bottom() - fraction * bounds.height()
            p.drawLine(int(bounds.left()), int(y), int(bounds.right()), int(y))
            p.setPen(QColor(MUTED))
            p.drawText(0, int(y) + 4, f"{fraction * maximum:.0f}")
            p.setPen(QColor("#30392a"))
        p.setPen(QColor(MUTED))
        p.drawText(
            40,
            self.height() - 5,
            self.unit + "  ·  " + ("Recent samples" if self.limit else "Sample order"),
        )
        if not self.values:
            p.drawText(bounds, Qt.AlignmentFlag.AlignCenter, "No measurements yet")
            return
        path = QPainterPath()
        for i, value in enumerate(self.values):
            x = bounds.left() + i / max(1, len(self.values) - 1) * bounds.width()
            y = (
                bounds.bottom()
                - min(maximum, max(0, value)) / maximum * bounds.height()
            )
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        p.setPen(QPen(QColor(ACCENT), 2))
        p.drawPath(path)


class Histogram(QWidget):
    def __init__(self):
        super().__init__()
        self.values = []
        self.setMinimumHeight(160)

    def set_values(self, values):
        self.values = list(values)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor(MUTED))
        if not self.values:
            p.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Import a capture to see frame-time distribution",
            )
            return
        captions = ["<4", "4–8", "8–12", "12–16.7", "16.7–25", "25–50", "≥50"]
        peak = max(self.values) or 1
        width = self.width() / 7
        for i, v in enumerate(self.values):
            h = v / peak * (self.height() - 45)
            x = i * width + 8
            p.fillRect(QRectF(x, self.height() - 25 - h, width - 16, h), QColor(ACCENT))
            p.setPen(QColor(MUTED))
            p.drawText(
                QRectF(i * width, self.height() - 23, width, 22),
                Qt.AlignmentFlag.AlignCenter,
                captions[i] + " ms",
            )
            p.drawText(
                QRectF(i * width, self.height() - 44 - h, width, 20),
                Qt.AlignmentFlag.AlignCenter,
                str(v),
            )


def scroll_page():
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    body = QWidget()
    body.setObjectName("page")
    layout = QVBoxLayout(body)
    layout.setContentsMargins(28, 24, 28, 28)
    layout.setSpacing(20)
    layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
    scroll.setWidget(body)
    return scroll, body, layout


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())


class FlowLayout(QLayout):
    """Wrap command buttons at narrow widths rather than force horizontal scrolling."""

    def __init__(self, spacing=10):
        super().__init__()
        self.items = []
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self.items.append(item)

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        return self.items[index] if 0 <= index < len(self.items) else None

    def takeAt(self, index):
        return self.items.pop(index) if 0 <= index < len(self.items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.arrange(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.arrange(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.items:
            size = size.expandedTo(item.minimumSize())
        return size

    def arrange(self, rect, test=False):
        x = rect.x()
        y = rect.y()
        height = 0
        for item in self.items:
            size = item.sizeHint()
            w = min(size.width(), rect.width())
            if x > rect.x() and x + w > rect.right() + 1:
                x = rect.x()
                y += height + self.spacing()
                height = 0
            if not test:
                item.setGeometry(QRect(QPoint(x, y), QSize(w, size.height())))
            x += w + self.spacing()
            height = max(height, size.height())
        return y + height - rect.y()


class ComparisonChart(QWidget):
    def __init__(self):
        super().__init__()
        self.metrics = {}
        self.setMinimumHeight(210)

    def set_metrics(self, metrics):
        self.metrics = metrics
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.metrics:
            p.setPen(QColor(MUTED))
            p.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Compare repeated runs to see before / after",
            )
            return
        for i, (name, m) in enumerate(self.metrics.items()):
            y = 18 + i * 43
            maximum = max(m["before_mean"], m["after_mean"]) or 1
            p.setPen(QColor(MUTED))
            p.drawText(0, y + 9, name.replace("_", " "))
            width = max(50, self.width() - 350)
            for j, (key, color) in enumerate(
                [("before_mean", "#5a6850"), ("after_mean", ACCENT)]
            ):
                p.fillRect(
                    QRectF(115, y + j * 12, width * m[key] / maximum, 8), QColor(color)
                )
            unit = "ms" if name == "p99_ms" else "FPS"
            p.setPen(QColor("#d1dbc9"))
            p.drawText(
                125 + int(width),
                y + 14,
                f"{m['before_mean']:.1f} → {m['after_mean']:.1f} {unit}",
            )
        p.setPen(QColor(MUTED))
        p.drawText(
            0,
            self.height() - 8,
            "Gray: before  ·  Lime: after  ·  Each metric uses its own scale",
        )
