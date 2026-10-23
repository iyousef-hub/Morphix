'''Native bounded page-range forms for Extract Range and Separate PDF.'''
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QMessageBox, QScrollArea, QWidget)
from page_ranges import validate_ranges
from i18n import tr

class PageRangeDialog(QDialog):
    def __init__(self, page_count, *, separate=False, parent=None):
        super().__init__(parent)
        self.page_count = int(page_count)
        self.separate = separate
        self.setWindowTitle(tr('Morphix · Separate PDF') if separate else tr('Morphix · Extract pages'))
        self.setMinimumWidth(420)
        self.setMaximumHeight(680)
        self.rows = []
        layout = QVBoxLayout(self)
        heading = QLabel(tr('This PDF has {n} pages. Choose page numbers from 1 to {n}.', n=page_count))
        heading.setWordWrap(True)
        layout.addWidget(heading)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        widget = QWidget()
        widget.setObjectName('rangeBody')
        self.range_layout = QVBoxLayout(widget)
        self.range_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(widget)
        layout.addWidget(scroll)
        self.add_row(1, min(page_count, 10) if separate else page_count)
        if separate:
            self.add_button = QPushButton(tr('+ Add another part'))
            self.add_button.clicked.connect(self.add_next)
            layout.addWidget(self.add_button)
        footer = QHBoxLayout()
        cancel = QPushButton(tr('Cancel'))
        cancel.clicked.connect(self.reject)
        run = QPushButton(tr('Separate PDF') if separate else tr('Extract pages'))
        run.setObjectName('primary')
        run.clicked.connect(self.check_and_accept)
        footer.addStretch()
        footer.addWidget(cancel)
        footer.addWidget(run)
        layout.addLayout(footer)
        self.setStyleSheet('''QDialog {background:#0B182C; color:#E9F4FF;} QLabel{color:#BCD9F6; background:transparent;}
        QScrollArea, QScrollArea > QWidget > QWidget, QWidget#rangeBody {background:transparent;}
        QPushButton{padding:9px 12px; background:#163657; border:1px solid #376391;
        border-radius:8px; color:#ECF6FF;} QPushButton:hover{background:#215181;}
        QPushButton#primary{background:#287BE2;} QSpinBox{padding:7px; min-width:76px;
        background:#122943; color:white; border:1px solid #456B93; border-radius:6px;}''')

    def add_row(self, start=1, end=None):
        end = self.page_count if end is None else end
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 3, 0, 3)
        lay.addWidget(QLabel(tr('Part {n}', n=len(self.rows)+1) if self.separate else tr('Pages')))
        first = QSpinBox()
        first.setRange(1, self.page_count)
        first.setValue(min(start, self.page_count))
        last = QSpinBox()
        last.setRange(1, self.page_count)
        last.setValue(min(end, self.page_count))
        lay.addWidget(QLabel(tr('From')))
        lay.addWidget(first)
        lay.addWidget(QLabel(tr('To')))
        lay.addWidget(last)
        if self.separate:
            remove = QPushButton('−')
            remove.setToolTip(tr('Remove this part'))
            remove.clicked.connect(lambda: self.remove_row(row))
            lay.addWidget(remove)
        self.range_layout.addWidget(row)
        self.rows.append((row, first, last))

    def add_next(self):
        if len(self.rows) >= self.page_count:
            QMessageBox.information(self, tr('No more parts'), tr('There cannot be more parts than pages.'))
            return
        if not self.rows:
            self.add_row(1, self.page_count)
            return
        last_first = self.rows[-1][1]
        last_end = self.rows[-1][2]
        if last_end.value() >= self.page_count:
            # Divide the final range automatically, so successive + clicks
            # never create an accidental out-of-bounds/overlapping section.
            if last_first.value() >= last_end.value():
                QMessageBox.information(self, tr('Adjust the last part'),
                    tr('The last part has only one page. Shorten or remove another part first.'))
                return
            midpoint = (last_first.value() + last_end.value()) // 2
            last_end.setValue(midpoint)
            start = midpoint + 1
        else:
            start = last_end.value() + 1
        self.add_row(start, self.page_count)
        self.adjustSize()

    def remove_row(self, widget):
        if len(self.rows) < 2:
            QMessageBox.information(self, tr('Keep one part'), tr('At least one page range is required.'))
            return
        self.rows = [r for r in self.rows if r[0] is not widget]
        self.range_layout.removeWidget(widget)
        widget.deleteLater()
        for i,(w,_,_) in enumerate(self.rows, 1):
            w.layout().itemAt(0).widget().setText(tr('Part {n}', n=i))

    def ranges(self):
        return [(first.value(),last.value()) for _,first,last in self.rows]

    def check_and_accept(self):
        try:
            validate_ranges(self.ranges(), self.page_count)
        except ValueError as exc:
            QMessageBox.warning(self, tr('Check the page ranges'), str(exc))
            return
        self.accept()


def ask_pdf_ranges(paths, *, separate=False, parent=None):
    import pymupdf
    if len(paths) != 1:
        QMessageBox.information(parent, tr('Select one PDF'), tr('Select a single PDF for page tools.'))
        return None
    with pymupdf.open(paths[0]) as doc:
        page_count = len(doc)
    dialog = PageRangeDialog(page_count, separate=separate, parent=parent)
    return dialog.ranges() if dialog.exec() == QDialog.Accepted else None
