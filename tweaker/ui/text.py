"""Selectable plain labels whose measured and painted text genuinely wraps.

QLabel's plain WordWrap keeps an unbroken model/path as its minimum width.
Use a text document with WrapAtWordBoundaryOrAnywhere for both geometry and
painting; never elide the text or alter the string copied to the clipboard.
"""

import math
from PySide6.QtCore import Qt, QSize, QPointF, QEvent
from PySide6.QtGui import (
    QPainter,
    QTextDocument,
    QTextOption,
    QTextCursor,
    QAbstractTextDocumentLayout,
    QPalette,
    QKeySequence,
)
from PySide6.QtWidgets import QLabel, QFrame, QMenu, QApplication


class WrappingLabel(QLabel):
    def __init__(self, text=""):
        super().__init__(text)
        self._document = QTextDocument(self)
        self._document.setDocumentMargin(0)
        option = self._document.defaultTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self._document.setDefaultTextOption(option)
        self._document.setPlainText(text)
        self._anchor = self._position = 0
        self.setWordWrap(True)

    def setText(self, text):
        super().setText(text)
        if hasattr(self, "_document"):
            self._document.setPlainText(text)
            self._anchor = self._position = 0
            self.updateGeometry()
            self.update()

    def _insets(self):
        m = self.contentsMargins()
        return (
            m.left() + m.right() + 2 * self.margin(),
            m.top() + m.bottom() + 2 * self.margin(),
        )

    def _measure(self, width):
        self._document.setDefaultFont(self.font())
        option = self._document.defaultTextOption()
        option.setAlignment(
            self.alignment()
            & (
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignHCenter
                | Qt.AlignmentFlag.AlignJustify
            )
        )
        self._document.setDefaultTextOption(option)
        self._document.setTextWidth(max(1, width))
        return math.ceil(self._document.size().height())

    def minimumSizeHint(self):
        horizontal, vertical = self._insets()
        return QSize(
            max(
                [1]
                + [
                    self.fontMetrics().horizontalAdvance(char)
                    for char in set(self.text())
                    if not char.isspace()
                ]
            )
            + horizontal,
            self.fontMetrics().height() + vertical,
        )

    def sizeHint(self):
        if not hasattr(self, "_document"):
            return super().sizeHint()
        horizontal, vertical = self._insets()
        self._document.setDefaultFont(self.font())
        self._document.setTextWidth(-1)
        # A preferred line length, not a mandatory width. Height-for-width is
        # recalculated for every actual allocation, including large system fonts.
        preferred = min(
            math.ceil(self._document.idealWidth()),
            max(120, self.fontMetrics().averageCharWidth() * 60),
        )
        return QSize(preferred + horizontal, self._measure(preferred) + vertical)

    def heightForWidth(self, width):
        if not hasattr(self, "_document"):
            return super().heightForWidth(width)
        horizontal, vertical = self._insets()
        return self._measure(max(1, width - horizontal)) + vertical

    def _origin(self):
        rect = self.contentsRect()
        self._measure(max(1, rect.width() - 2 * self.margin()))
        y = rect.top() + self.margin()
        spare = rect.height() - 2 * self.margin() - self._document.size().height()
        if self.alignment() & Qt.AlignmentFlag.AlignVCenter:
            y += max(0, spare / 2)
        elif self.alignment() & Qt.AlignmentFlag.AlignBottom:
            y += max(0, spare)
        return QPointF(rect.left() + self.margin(), y)

    def paintEvent(self, event):
        QFrame.paintEvent(self, event)
        painter = QPainter(self)
        origin = self._origin()
        painter.translate(origin)
        context = QAbstractTextDocumentLayout.PaintContext()
        context.palette = self.palette()
        provider = getattr(self.parentWidget(), "caption_color", None)
        foreground = (
            provider()
            if callable(provider)
            else self.palette().color(QPalette.ColorRole.WindowText)
        )
        context.palette.setColor(QPalette.ColorRole.Text, foreground)
        if self._anchor != self._position:
            selection = QAbstractTextDocumentLayout.Selection()
            selection.cursor = QTextCursor(self._document)
            selection.cursor.setPosition(min(self._anchor, self._position))
            selection.cursor.setPosition(
                max(self._anchor, self._position), QTextCursor.MoveMode.KeepAnchor
            )
            selection.format.setBackground(self.palette().highlight())
            selection.format.setForeground(self.palette().highlightedText())
            context.selections = [selection]
        self._document.documentLayout().draw(painter, context)

    def changeEvent(self, event):
        super().changeEvent(event)
        if hasattr(self, "_document") and event.type() in (
            QEvent.Type.FontChange,
            QEvent.Type.StyleChange,
        ):
            self._document.setDefaultFont(self.font())
            self.updateGeometry()
            self.update()

    def _hit(self, position):
        index = self._document.documentLayout().hitTest(
            position - self._origin(), Qt.HitTestAccuracy.FuzzyHit
        )
        return max(0, min(self._document.characterCount() - 1, index))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._anchor = self._position = self._hit(event.position())
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self.update()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._position = self._hit(event.position())
            self.update()
        else:
            super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        cursor = QTextCursor(self._document)
        cursor.setPosition(self._hit(event.position()))
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        self._anchor, self._position = cursor.selectionStart(), cursor.selectionEnd()
        self.update()

    def selected_text(self):
        start, end = sorted((self._anchor, self._position))
        if start == 0 and end == self._document.characterCount() - 1:
            return self.text()
        cursor = QTextCursor(self._document)
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        return cursor.selectedText().replace("\u2029", "\n")

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.SelectAll):
            self._anchor, self._position = 0, self._document.characterCount() - 1
            self.update()
        elif event.matches(QKeySequence.StandardKey.Copy):
            QApplication.clipboard().setText(self.selected_text())
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        copy = menu.addAction("Copy")
        copy.setEnabled(self._anchor != self._position)
        all_text = menu.addAction("Select all")
        choice = menu.exec(event.globalPos())
        if choice == all_text:
            self._anchor, self._position = 0, self._document.characterCount() - 1
            self.update()
        elif choice == copy:
            QApplication.clipboard().setText(self.selected_text())
