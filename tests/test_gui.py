import os
import tempfile
import unittest
from unittest.mock import patch
try:
    import tkinter as tk
except ImportError:
    tk=None

@unittest.skipUnless(tk is not None and (os.name=='nt' or os.environ.get('DISPLAY')),'Tk/display unavailable')
class GuiSmokeTests(unittest.TestCase):
    def setUp(self):
        from tweaker.gui import App
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.environment=patch.dict(os.environ,{'LOCALAPPDATA':self.tmp.name}); self.environment.start(); self.addCleanup(self.environment.stop)
        self.root=tk.Tk(); self.root.withdraw()
        self.app=App(self.root); self.root.update()
    def tearDown(self):
        self.app.shutdown()
        self.root.destroy()
    def test_search_category_and_individual_toggle(self):
        self.app.search.set('power'); self.root.update()
        self.assertEqual(len(self.app.action_tree.get_children()),2)
        self.app.category.set('Services'); self.root.update()
        self.assertFalse(self.app.action_tree.get_children())
        self.app.search.set(''); self.root.update()
        self.app.action_tree.selection_set('service.fax'); self.app.toggle_action()
        self.assertTrue(self.app.choices['service.fax'].get())
        self.app.action_detail()
        self.assertIn('Fax',self.app.details.get('1.0','end'))
    def test_pages_and_charts(self):
        for page in self.app.pages.values():
            self.app.tabs.select(page); self.root.update()
        self.app.draw([1,2,3,4,5,6,7])
        self.assertEqual(len(self.app.chart.find_all()),21)
        self.app.draw_comparison({'metrics':{'average_fps':{'before_mean':100,'after_mean':110,'percent':10}}})
        self.assertGreater(len(self.app.chart.find_all()),3)
    def test_mock_state_inspection_and_restore(self):
        from tweaker.engine import Engine
        from tweaker.platform import MockBackend
        self.app.engine=Engine(MockBackend(),self.tmp.name)
        self.app.engine.apply('power.high')
        self.app.update_states(self.app.states())
        self.assertIn('ACTIVE',self.app.action_tree.item('power.high')['values'][-1])
        self.app.engine.restore_all()
        self.app.update_states(self.app.states())
        self.assertNotIn('ACTIVE',self.app.action_tree.item('power.high')['values'][-1])
