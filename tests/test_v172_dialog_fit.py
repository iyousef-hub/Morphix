"""v1.7.2: dialogs grow to fit word-wrapped text instead of squeezing it."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QComboBox


def test_dialog_grows_to_wrapped_content():
    app = QApplication.instance() or QApplication([])
    import theme
    d = QDialog()
    lay = QVBoxLayout(d)
    text = QLabel('word ' * 200)
    text.setWordWrap(True)
    lay.addWidget(text)
    lay.addWidget(QComboBox())
    d.resize(400, 60)
    theme.fit_height(d)
    assert d.height() >= lay.totalHeightForWidth(d.width())
