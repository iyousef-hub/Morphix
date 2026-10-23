"""Morphix: lightweight startup splash and contact dialog (local/offline)."""
from pathlib import Path
from PySide6.QtCore import Qt, QPropertyAnimation, QTimer, QEasingCurve
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QLinearGradient, QDesktopServices, QPixmap, QIcon
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGraphicsOpacityEffect, QFrame
)

from app_assets import logo_png
from i18n import tr

LINKEDIN_URL = "https://www.linkedin.com/in/yousef-alghamdi-793345267/"
GITHUB_URL = "https://github.com/iyousef-hub"
CONTACT_EMAIL = "youssefbinaziz@gmail.com"


class _SplashBackground(QWidget):
    """Draws a rounded translucent blue glass surface without asset dependencies."""
    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        bounds = self.rect().adjusted(2, 2, -2, -2)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor(7, 22, 47, 245))
        gradient.setColorAt(0.58, QColor(13, 40, 82, 238))
        gradient.setColorAt(1.0, QColor(23, 65, 124, 230))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(136, 187, 255, 100), 1.1))
        painter.drawRoundedRect(bounds, 27, 27)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(76, 147, 255, 22))
        painter.drawEllipse(self.width()-185, -75, 250, 250)
        painter.setBrush(QColor(66, 128, 255, 15))
        painter.drawEllipse(-95, 170, 230, 230)


class SplashDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(470, 285)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        bg = _SplashBackground()
        root.addWidget(bg)
        content = QVBoxLayout(bg)
        content.setContentsMargins(20, 16, 20, 22)
        content.setSpacing(7)
        content.addStretch(1)
        emblem = QLabel()
        emblem.setAlignment(Qt.AlignCenter)
        emblem.setStyleSheet('background: transparent;')
        emblem.setPixmap(QPixmap(logo_png()).scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        content.addWidget(emblem)
        title = QLabel('Morphix')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('color: #EAF4FF; font-size: 39px; font-weight: 800; background: transparent;')
        content.addWidget(title)
        byline = QLabel(tr('By Yousef'))
        byline.setAlignment(Qt.AlignCenter)
        font = QFont('Arial', 15)
        font.setItalic(True)
        byline.setFont(font)
        byline.setStyleSheet('color: #B4D6FF; background: transparent;')
        content.addWidget(byline)
        content.addSpacing(12)
        tagline = QLabel(tr('Your files, transformed.'))
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setStyleSheet('color: #7FA8D8; font-size: 11px; background: transparent;')
        content.addWidget(tagline)
        content.addStretch(1)
        fade_effect = QGraphicsOpacityEffect(bg)
        bg.setGraphicsEffect(fade_effect)
        fade_effect.setOpacity(0.0)
        self._fade_in = QPropertyAnimation(fade_effect, b'opacity', self)
        self._fade_in.setDuration(350)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)

    def showEvent(self, event):
        super().showEvent(event)
        self._fade_in.start()
        QTimer.singleShot(1150, self.accept)


class AboutDialog(QDialog):
    """Developer links; no user feedback forms or external data requests."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('About Morphix'))
        self.setMinimumWidth(620)
        self.setModal(True)
        self.setStyleSheet('''
            QDialog { background: #09172B; color: #EFF6FF; }
            QLabel { background: transparent; color: #DCEBFF; }
            QPushButton { background: #132D52; color: #EDF6FF; border: 1px solid #284B78;
                border-radius: 11px; padding: 11px 14px; font-size: 13px; }
            QPushButton:hover { background: #1D4478; border: 1px solid #599EFE; }
        ''')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(about_content(self))
        close = QPushButton(tr('Close'))
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close)
        layout.addLayout(row)

MISSION = ('Morphix was designed and built to save you time and effort: it brings your everyday file '
           'tools together in one place, so the work gets done in a single step — privately, on your own '
           'computer, without needing the internet.')
DEVELOPER = 'Yousef A.Alghamdi'


FREE_NOTE = 'Completely free — no subscriptions, no ads, and no account needed.'


def about_content(parent=None):
    """Centered About card: logo, name, version, mission, free note, developer, contacts."""
    from PySide6.QtWidgets import QSizePolicy
    box = QWidget(parent)
    box.setObjectName('aboutBox')
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 6, 0, 0)
    lay.setSpacing(10)
    center = Qt.AlignHCenter

    logo = QLabel()
    logo.setPixmap(QPixmap(logo_png()).scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    logo.setAlignment(Qt.AlignCenter)
    lay.addWidget(logo)
    title = QLabel('Morphix')
    title.setAlignment(Qt.AlignCenter)
    title.setStyleSheet('font-size: 34px; font-weight: 800; color: #A6D4FF; background: transparent;')
    lay.addWidget(title)
    try:
        from main import APP_VERSION
    except Exception:
        APP_VERSION = ''
    tag = QLabel(tr('Your files, transformed.') + ('   ·   ' + tr('Version {v}', v=APP_VERSION) if APP_VERSION else ''))
    tag.setAlignment(Qt.AlignCenter)
    tag.setStyleSheet('color: #8FA9C9; font-size: 13px; background: transparent;')
    lay.addWidget(tag)
    lay.addSpacing(8)

    card = QFrame()
    card.setObjectName('missionCard')
    card.setStyleSheet('QFrame#missionCard { background:#112743; border:1px solid #2C5582; border-radius:16px; }')
    card.setMaximumWidth(640)
    cl = QVBoxLayout(card)
    cl.setContentsMargins(24, 20, 24, 20)
    cl.setSpacing(14)
    mission = QLabel(tr(MISSION))
    mission.setWordWrap(True)
    mission.setAlignment(Qt.AlignCenter)
    mission.setStyleSheet('color:#E2EEFC; font-size:15px; background:transparent;')
    cl.addWidget(mission)
    free = QLabel('✓  ' + tr(FREE_NOTE))
    free.setWordWrap(True)
    free.setAlignment(Qt.AlignCenter)
    free.setStyleSheet('color:#8FF0D7; font-size:14px; font-weight:700; background:#0F3540; '
                       'border:1px solid #24606F; border-radius:10px; padding:9px 12px;')
    cl.addWidget(free)
    holder = QHBoxLayout()            # centres the card; wrapped text keeps its full height
    holder.addStretch(1)
    holder.addWidget(card, 20)
    holder.addStretch(1)
    lay.addLayout(holder)
    lay.addSpacing(12)

    dev = QLabel(tr(DEVELOPER))
    dev.setAlignment(Qt.AlignCenter)
    dev.setStyleSheet('color:#C9DBF2; font-size:14px; font-weight:600; background:transparent;')
    lay.addWidget(dev)
    row = QHBoxLayout()
    row.setSpacing(10)
    row.addStretch(1)
    for text, url, icon in (('LinkedIn', LINKEDIN_URL, None),
                            ('GitHub', GITHUB_URL, 'github_mark.png'),
                            (tr('Email'), 'mailto:' + CONTACT_EMAIL, None)):
        btn = QPushButton(text + '  ↗')
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip(url.replace('mailto:', ''))
        if icon:
            btn.setIcon(QIcon(str(Path(__file__).parent / 'assets' / icon)))
        btn.setMinimumWidth(130)
        btn.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
        row.addWidget(btn)
    row.addStretch(1)
    lay.addLayout(row)
    mail = QLabel(CONTACT_EMAIL)
    mail.setAlignment(Qt.AlignCenter)
    mail.setStyleSheet('color:#6F8BAD; font-size:12px; background:transparent;')
    mail.setTextInteractionFlags(Qt.TextSelectableByMouse)
    lay.addWidget(mail)
    lay.addStretch(1)
    return box
