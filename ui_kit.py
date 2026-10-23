"""Small widgets that behave correctly in both English and Arabic (RTL)."""
from __future__ import annotations

from PySide6.QtCore import Qt, QRect, QSize, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import (QToolButton, QHBoxLayout, QLabel, QStyledItemDelegate, QStyle,
                               QSizePolicy)

import i18n


class NavButton(QToolButton):
    """Sidebar entry. English: ‘◎  Action Hub’ aligned left.
    Arabic: ‘مركز الأدوات  ◎’ aligned right — the symbol comes after the words."""

    def __init__(self, text, glyph='', checkable=False, parent=None):
        super().__init__(parent)
        self.setCheckable(checkable)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName('navButton')
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(9)
        self.text_label = QLabel(text)
        self.text_label.setObjectName('navText')
        self.glyph_label = QLabel(glyph)
        self.glyph_label.setObjectName('navGlyph')
        for lbl in (self.text_label, self.glyph_label):
            lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        if i18n.is_rtl():
            # Layouts mirror in RTL: the first item is drawn on the right.
            lay.addWidget(self.text_label)
            if glyph:
                lay.addWidget(self.glyph_label)
        else:
            if glyph:
                lay.addWidget(self.glyph_label)
            lay.addWidget(self.text_label)
        lay.addStretch(1)
        self.setMinimumHeight(40)

    def sizeHint(self):
        return self.layout().sizeHint().expandedTo(QSize(120, 40))

    def setText(self, text):  # keep QToolButton's own text empty
        if hasattr(self, 'text_label'):
            self.text_label.setText(text)


NAV_CSS = '''
QToolButton#navButton { background: transparent; border: 0; border-radius: 10px; }
QToolButton#navButton:hover { background: #1B3152; }
QToolButton#navButton:checked { background: #2367BC; }
QToolButton#navButton QLabel { background: transparent; color: #B6C7E0; font-size: 14px; }
QToolButton#navButton:checked QLabel { color: #FFFFFF; font-weight: bold; }
QToolButton#navButton:hover QLabel { color: #FFFFFF; }
'''


class ToolListDelegate(QStyledItemDelegate):
    """Draws each tool row with our own tick box, so every row shows its state
    (macOS drew only one checkbox for right-to-left lists). Arabic order from the
    right: tick · words · symbol."""

    def __init__(self, accent='#3F8CF0', parent=None):
        super().__init__(parent)
        self.accent = QColor(accent)

    def sizeHint(self, option, index):
        return QSize(10, 44)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        r = option.rect.adjusted(2, 2, -2, -2)
        if option.state & QStyle.State_MouseOver:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#1D3656'))
            painter.drawRoundedRect(r, 8, 8)
        checked = index.data(Qt.CheckStateRole) == Qt.Checked
        rtl = i18n.is_rtl()
        box = QRect(0, 0, 20, 20)
        box.moveCenter(r.center())
        box.moveLeft(r.right() - 32) if rtl else box.moveLeft(r.left() + 12)
        painter.setPen(QPen(self.accent if checked else QColor('#5C7899'), 1.6))
        painter.setBrush(self.accent if checked else Qt.NoBrush)
        painter.drawRoundedRect(QRectF(box), 5, 5)
        if checked:
            painter.setPen(QPen(QColor('white'), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            from PySide6.QtCore import QPointF
            b = QRectF(box)
            painter.drawPolyline([QPointF(b.left() + 5, b.top() + 10.5), QPointF(b.left() + 8.5, b.top() + 14),
                                  QPointF(b.left() + 15, b.top() + 6.5)])
        text = index.data(Qt.DisplayRole) or ''
        icon = index.data(Qt.DecorationRole)
        font = QFont(option.font)
        font.setPointSizeF(font.pointSizeF() + 1)
        painter.setFont(font)
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(text)
        painter.setPen(QColor('#EAF3FF') if checked else QColor('#8EA6C4'))
        if rtl:
            text_rect = QRect(box.left() - 14 - tw, r.top(), tw, r.height())
            icon_x = text_rect.left() - 12 - 22
        else:
            text_rect = QRect(box.right() + 14, r.top(), tw, r.height())
            icon_x = None
        if rtl:
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignRight, text)
            if icon is not None:
                icon.paint(painter, QRect(icon_x, r.center().y() - 11, 22, 22))
        else:
            if icon is not None:
                icon.paint(painter, QRect(text_rect.left(), r.center().y() - 11, 22, 22))
                text_rect.moveLeft(text_rect.left() + 32)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            state = index.data(Qt.CheckStateRole)
            model.setData(index, Qt.Unchecked if state == Qt.Checked else Qt.Checked, Qt.CheckStateRole)
            return True
        return False
