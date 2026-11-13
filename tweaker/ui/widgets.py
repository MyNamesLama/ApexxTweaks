"""Reusable cards, accessible switches and cheap-on-idle painted plots."""

import math
from PySide6.QtCore import Qt, QRectF, QSize, QRect
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
from .text import WrappingLabel


def label(text="", role="", wrap=True):
    wrapping = wrap and role not in ("tag", "limeTag")
    w = WrappingLabel(text) if wrapping else QLabel(text)
    w.setTextFormat(Qt.TextFormat.PlainText)
    if role:
        w.setObjectName(role)
    w.setWordWrap(wrapping)
    w.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return w


def button(text, callback, primary=False, danger=False):
    w = WrappingButton(text)
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

    def responsive_width_hint(self):
        values = [
            child
            for child in self.findChildren(QLabel)
            if child.objectName() == "metric"
        ]
        return max(
            [0]
            + [
                min(400, child.fontMetrics().horizontalAdvance(child.text()) + 44)
                for child in values
            ]
        )


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
    """Height-for-width rows: wrap complete controls and fully measure wrapped text."""

    def __init__(self, spacing=10):
        super().__init__()
        self.items = []
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self.items.append(item)
        self.invalidate()

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        return self.items[index] if 0 <= index < len(self.items) else None

    def takeAt(self, index):
        if 0 <= index < len(self.items):
            result = self.items.pop(index)
            self.invalidate()
            return result
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.arrange(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.arrange(rect)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize(0, 0)
        for item in self.items:
            if not item.isEmpty():
                size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(
            margins.left() + margins.right(), margins.top() + margins.bottom()
        )

    @staticmethod
    def item_height(item, width):
        height = (
            item.heightForWidth(width)
            if item.hasHeightForWidth()
            else item.sizeHint().height()
        )
        return max(item.minimumSize().height(), height)

    def arrange(self, rect, test=False):
        m = self.contentsMargins()
        area = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x = area.x()
        y = area.y()
        height = 0
        for item in self.items:
            if item.isEmpty():
                continue
            size = item.sizeHint()
            width = min(
                max(size.width(), item.minimumSize().width()), max(1, area.width())
            )
            if x > area.x() and x + width > area.right() + 1:
                x = area.x()
                y += height + self.spacing()
                height = 0
            item_height = self.item_height(item, width)
            if not test:
                item.setGeometry(QRect(x, y, width, item_height))
            x += width + self.spacing()
            height = max(height, item_height)
        return y + height - rect.y() + m.bottom()


class ResponsiveGrid(FlowLayout):
    """Ordered equal-width cards, with real font/content-driven 1..N column reflow.

    A compact minimum is valid because the geometry actually stacks all children
    and reports the full resulting height. No controls are hidden or compressed.
    """

    def __init__(self, max_columns=3, preferred_width=240, spacing=14):
        super().__init__(spacing)
        self.max_columns = max_columns
        self.preferred_width = preferred_width
        self.columns = 1

    def column_count(self, width):
        active = [item for item in self.items if not item.isEmpty()]
        if not active:
            return 1
        preferred = max(
            self.preferred_width,
            self.minimumSize().width(),
            *(
                item.widget().responsive_width_hint()
                if hasattr(item.widget(), "responsive_width_hint")
                else 0
                for item in active
            ),
        )
        return max(
            1,
            min(
                self.max_columns,
                len(active),
                (max(0, width) + self.spacing()) // (preferred + self.spacing()),
            ),
        )

    def arrange(self, rect, test=False):
        m = self.contentsMargins()
        area = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        active = [item for item in self.items if not item.isEmpty()]
        columns = self.column_count(area.width())
        if not test:
            self.columns = columns
        gap = self.spacing()
        width = max(1, (area.width() - (columns - 1) * gap) // columns)
        y = area.y()
        for start in range(0, len(active), columns):
            group = active[start : start + columns]
            row_height = max(self.item_height(item, width) for item in group)
            if not test:
                for column, item in enumerate(group):
                    cell_width = (
                        width
                        if column < columns - 1
                        else max(
                            1, area.right() + 1 - (area.x() + column * (width + gap))
                        )
                    )
                    item.setGeometry(
                        QRect(
                            area.x() + column * (width + gap), y, cell_width, row_height
                        )
                    )
            y += row_height + gap
        return y - rect.y() - (gap if active else 0) + m.bottom()


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


class WrappingButton(QPushButton):
    """Native button behavior with a real height-for-width, selectable-size caption."""

    def __init__(self, text):
        super().__init__()
        from PySide6.QtWidgets import QHBoxLayout

        self._caption_text = text
        self._nav_icon = None
        self._nav_icon_size = QSize(20, 20)
        self.setStyleSheet("QPushButton { padding: 0; }")
        box = QHBoxLayout(self)
        box.setContentsMargins(14, 9, 14, 9)
        box.setSpacing(10)
        self.picture = QLabel()
        self.picture.setFixedSize(self._nav_icon_size)
        self.picture.hide()
        self.caption = label(text.strip())
        self.caption.setObjectName("buttonCaption")
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.caption.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for child in (self.picture, self.caption):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        box.addWidget(self.picture)
        box.addWidget(self.caption, 1)
        policy = self.sizePolicy()
        policy.setHorizontalPolicy(QSizePolicy.Policy.Preferred)
        policy.setVerticalPolicy(QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setAccessibleName(text)
        self.toggled.connect(lambda _: self.caption.update())

    def caption_color(self):
        # Qt ancestor pseudo-states do not consistently resolve child palettes.
        role = self.objectName()
        if not self.isEnabled():
            return QColor("#b0b99f" if role == "primary" else "#778072")
        if role == "primary":
            return QColor("#152007")
        if role == "danger":
            return QColor("#f0bca1")
        if role == "nav":
            return QColor("#c8ff68" if self.isChecked() else "#aab2a6")
        if role == "collapse":
            return QColor("#aab2a6")
        return QColor("#f2f4ef")

    def changeEvent(self, event):
        super().changeEvent(event)
        if hasattr(self, "caption"):
            self.caption.update()

    def setText(self, text):
        self._caption_text = text
        self.caption.setText(text.strip())
        self.caption.setVisible(bool(text.strip()))
        self.updateGeometry()

    def text(self):
        return self._caption_text

    def setIcon(self, icon):
        self._nav_icon = icon
        self.picture.setPixmap(icon.pixmap(self._nav_icon_size))
        self.picture.show()
        self.updateGeometry()

    def setIconSize(self, size):
        self._nav_icon_size = size
        self.picture.setFixedSize(size)
        if self._nav_icon is not None:
            self.picture.setPixmap(self._nav_icon.pixmap(size))

    def sizeHint(self):
        return self.layout().totalSizeHint() if self.layout() else super().sizeHint()

    def minimumSizeHint(self):
        return (
            self.layout().totalMinimumSize()
            if self.layout()
            else super().minimumSizeHint()
        )

    def heightForWidth(self, width):
        return (
            self.layout().totalHeightForWidth(width)
            if self.layout()
            else super().heightForWidth(width)
        )


class NavigationButton(WrappingButton):
    """Checkable sidebar caption remains readable with large system font metrics."""

    def __init__(self, text):
        super().__init__(text)
        self.setObjectName("nav")
        self.layout().setContentsMargins(12, 10, 12, 10)
        self.caption.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
