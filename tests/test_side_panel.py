# -*- coding: utf-8 -*-
"""右侧面板 RightPanel(选项卡式)API 的单元测试(offscreen)。

钉死:add_section 新增与同 key 替换、remove_section 清理、关闭分区发 section_closed、
全空发 closed、不可关闭分区无 ✕、旧 set_content/clear_content 兼容。
"""
import os
import unittest
import warnings

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
warnings.filterwarnings("ignore")

from PySide2.QtWidgets import QApplication, QLabel, QTabBar

from ui.widgets.side_panel import RightPanel

_app = QApplication.instance() or QApplication([])


def _tab_has_close(panel, key):
    bar = panel._tabs.tabBar()
    idx = panel._tabs.indexOf(panel._scrolls[key])
    return bool(bar.tabButton(idx, QTabBar.RightSide)
                or bar.tabButton(idx, QTabBar.LeftSide))


class TestSections(unittest.TestCase):
    def setUp(self):
        self.p = RightPanel()

    def test_add_and_keys(self):
        self.p.add_section("a", "甲", QLabel("A"))
        self.p.add_section("b", "乙", QLabel("B"))
        self.assertEqual(self.p.section_keys(), ["a", "b"])
        self.assertTrue(self.p.has_sections())

    def test_same_key_replaces(self):
        self.p.add_section("a", "甲", QLabel("A"))
        w2 = QLabel("A2")
        self.p.add_section("a", "甲改", w2)
        self.assertEqual(self.p.section_keys(), ["a"])   # 不新增
        self.assertIs(self.p._widgets["a"], w2)          # 内容已替换

    def test_remove(self):
        self.p.add_section("a", "甲", QLabel("A"))
        self.p.add_section("b", "乙", QLabel("B"))
        self.p.remove_section("a")
        self.assertEqual(self.p.section_keys(), ["b"])
        self.p.remove_section("b")
        self.assertFalse(self.p.has_sections())

    def test_close_signal(self):
        got = []
        self.p.section_closed.connect(got.append)
        emptied = []
        self.p.closed.connect(lambda: emptied.append(True))
        self.p.add_section("a", "甲", QLabel("A"), closable=True)
        idx = self.p._tabs.indexOf(self.p._scrolls["a"])
        self.p._on_tab_close_requested(idx)              # 模拟点选项卡 ✕
        self.assertEqual(got, ["a"])
        self.assertEqual(emptied, [True])                # 全空 -> closed

    def test_closable_tab_has_close_button(self):
        self.p.add_section("a", "甲", QLabel("A"), closable=True)
        self.assertTrue(_tab_has_close(self.p, "a"))

    def test_non_closable_has_no_close_button(self):
        self.p.add_section("preview", "文件预览", QLabel("P"), closable=False)
        self.assertFalse(_tab_has_close(self.p, "preview"))   # 预览分区无 ✕

    def test_non_closable_ignores_close_request(self):
        """预览分区即便走到关闭请求也不该被移除(双保险)。"""
        self.p.add_section("preview", "文件预览", QLabel("P"), closable=False)
        idx = self.p._tabs.indexOf(self.p._scrolls["preview"])
        self.p._on_tab_close_requested(idx)
        self.assertIn("preview", self.p.section_keys())

    def test_legacy_set_clear(self):
        self.p.set_content(QLabel("X"), "标题")
        self.assertEqual(self.p.section_keys(), ["main"])
        self.p.clear_content()
        self.assertFalse(self.p.has_sections())


class TestPreviewReopen(unittest.TestCase):
    """钉死已修复的崩溃:预览分区隐藏后再预览须重建、不得崩(悬垂 C++ 对象)。"""
    def setUp(self):
        import tempfile, openpyxl
        from ui.main_window import MainWindow
        from core import settings as settings_mod
        settings_mod.get_settings().set("preview_hidden", False)   # 隔离:清测试间污染
        self.w = MainWindow()
        self.tmp = tempfile.mkdtemp(prefix="fyt_prev_")
        self.p1 = os.path.join(self.tmp, "a.xlsx")
        self.p2 = os.path.join(self.tmp, "b.xlsx")
        for path, code in ((self.p1, "A1"), (self.p2, "B1")):
            wb = openpyxl.Workbook(); ws = wb.active
            ws.append(["物料号", "名称"]); ws.append([code, "x"]); wb.save(path)

    def tearDown(self):
        import shutil
        from core import settings as settings_mod
        settings_mod.get_settings().set("preview_hidden", False)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_preview_tab_not_closable(self):
        self.w.preview_file(self.p1)
        self.assertFalse(_tab_has_close(self.w._right_panel, "preview"))

    def test_hide_then_preview_again(self):
        from ui.main_window import _qt_alive
        self.w.preview_file(self.p1)
        self.w.toggle_panel()                        # 隐藏预览分区
        self.assertNotIn("preview", self.w._right_panel.section_keys())
        self.assertIsNone(self.w._preview_widget)    # 悬垂引用已清
        # 再预览应重建成功(旧代码此处 native crash)
        self.w.preview_file(self.p2)
        self.assertIn("preview", self.w._right_panel.section_keys())
        self.assertTrue(_qt_alive(self.w._preview_widget))


class TestSidebarLayout(unittest.TestCase):
    """钉死新布局约定:
    - 默认带"文件预览"选项卡、面板可见;
    - 顶栏切换钮只显隐预览,不动业务分区;
    - 业务分区是可独立关闭的选项卡;关掉最后一个分区面板自动收起;
    - 点文件即便之前隐了预览也恢复。"""
    def _pump(self, ms=350):
        import time
        end = time.time() + ms / 1000.0
        while time.time() < end:
            _app.processEvents(); time.sleep(0.01)

    def setUp(self):
        import tempfile, openpyxl
        from ui.main_window import MainWindow
        from core import settings as settings_mod
        settings_mod.get_settings().set("preview_hidden", False)   # 隔离:清测试间污染
        self.w = MainWindow(); self.w.resize(1200, 800); self.w.show()
        self._pump(400)
        self.tmp = tempfile.mkdtemp(prefix="fyt_lay_")
        self.f = os.path.join(self.tmp, "a.xlsx")
        wb = openpyxl.Workbook(); ws = wb.active
        ws.append(["x", "y"]); ws.append(["A", "B"]); wb.save(self.f)

    def tearDown(self):
        import shutil
        from core import settings as settings_mod
        settings_mod.get_settings().set("preview_hidden", False)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_default_preview_tab_visible(self):
        rp = self.w._right_panel
        self.assertTrue(rp.isVisible())
        self.assertEqual(rp.section_keys(), ["preview"])
        self.assertFalse(_tab_has_close(rp, "preview"))

    def test_business_tab_is_closable_and_independent(self):
        rp = self.w._right_panel
        self.w.open_panel(QLabel("复核"), "人工核对", key="review"); self._pump()
        self.assertEqual(set(rp.section_keys()), {"preview", "review"})
        self.assertTrue(_tab_has_close(rp, "review"))
        # 关掉业务分区 -> 预览仍在,面板仍展开
        idx = rp._tabs.indexOf(rp._scrolls["review"])
        rp._on_tab_close_requested(idx); self._pump()
        self.assertEqual(rp.section_keys(), ["preview"])
        self.assertTrue(rp.isVisible())

    def test_toggle_only_affects_preview(self):
        rp = self.w._right_panel
        self.w.open_panel(QLabel("复核"), "人工核对", key="review"); self._pump()
        self.w.toggle_panel(); self._pump()          # 隐藏预览
        self.assertTrue(self.w._preview_hidden)
        self.assertEqual(rp.section_keys(), ["review"])   # 业务分区不受影响
        self.assertTrue(rp.isVisible())

    def test_collapse_when_no_sections(self):
        rp = self.w._right_panel
        self.w.toggle_panel(); self._pump()          # 隐藏预览(此时只有预览)
        self.assertEqual(rp.section_keys(), [])
        self.assertFalse(rp.isVisible())             # 无分区 -> 自动收起

    def test_click_file_restores_hidden_preview(self):
        rp = self.w._right_panel
        self.w.toggle_panel(); self._pump()          # 先隐藏预览
        self.assertTrue(self.w._preview_hidden)
        self.w.preview_file(self.f); self._pump()    # 点文件应恢复预览
        self.assertFalse(self.w._preview_hidden)
        self.assertIn("preview", rp.section_keys())
        self.assertTrue(rp.isVisible())


if __name__ == "__main__":
    unittest.main()
