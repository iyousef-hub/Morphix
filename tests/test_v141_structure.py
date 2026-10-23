"""Release packaging regressions that can run without an installed GUI."""
from pathlib import Path
import ast
import unittest

ROOT=Path(__file__).resolve().parents[1]

class TestHotfixStructure(unittest.TestCase):
    def test_source_parses(self):
        ast.parse((ROOT/'main.py').read_text())
        ast.parse((ROOT/'quickwheel.py').read_text())

    def test_local_single_instance_before_splash(self):
        code=(ROOT/'main.py').read_text()
        self.assertIn('QLocalServer', code)
        self.assertIn('_single_instance_server(app)', code)
        self.assertIn('if instance_server is None:',code)
        self.assertLess(code.index('instance_server = _single_instance_server(app)'), code.index('SplashDialog().exec()'))

    def test_translucent_repaint(self):
        code=(ROOT/'quickwheel.py').read_text()
        self.assertIn('painter.setCompositionMode(QPainter.CompositionMode_Source)',code)
        self.assertIn('painter.fillRect(self.rect(), Qt.transparent)',code)
        self.assertIn('was_visible = self.isVisible()',code)
        self.assertIn('self.show_anim.stop()',code)
        self.assertIn('self.hide()',code)

    def test_escape_from_stuck_wheel(self):
        code=(ROOT/'quickwheel.py').read_text()
        self.assertIn("menu.addAction(tr('Hide the Action Hub'), self.hide_wheel)",code)
        self.assertIn("help_menu.addAction(tr('Reset the Action Hub appearance'), self.reset_wheel_appearance)",code)

    def test_launcher_avoids_old_dist(self):
        code=(ROOT/'Launch_Morphix_Mac.command').read_text()
        self.assertNotIn('open "$ROOT/dist/Morphix.app"',code)

if __name__=='__main__': unittest.main()
