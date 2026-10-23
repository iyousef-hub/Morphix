"""macOS GUI smoke test for the mixed-PDF ordering dialog (no file changes)."""
import sys
from PySide6.QtWidgets import QApplication
from merge_order_dialog import MergeOrderDialog

app = QApplication.instance() or QApplication(sys.argv)
dialog = MergeOrderDialog(['/tmp/a.png', '/tmp/b.jpeg', '/tmp/c.pdf'])
assert dialog.ordered_paths() == ['/tmp/a.png', '/tmp/b.jpeg', '/tmp/c.pdf']
dialog.files.setCurrentRow(2)
dialog.move_selected(-1)
assert dialog.ordered_paths() == ['/tmp/a.png', '/tmp/c.pdf', '/tmp/b.jpeg']
dialog.show()
app.processEvents()
assert dialog.isVisible()
dialog.close()
print('Morphix v1.4.5 order-dialog GUI smoke test: PASS')
