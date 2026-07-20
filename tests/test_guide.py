# -*- coding: utf-8 -*-
"""使用指引(聚光灯引导)冒烟测试(offscreen)。

钉死:有步骤的页显示「使用指引」按钮、无步骤的页不显示;覆盖层能开、
能前进/后退、走到末步「完成」触发 finished 并隐藏;送货页步骤覆盖关键控件。
"""
import os
import unittest
import warnings

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
warnings.filterwarnings("ignore")

from PySide2.QtWidgets import QApplication, QLabel

from ui.pages.base_page import BasePage
from ui.guide import GuideOverlay

_app = QApplication.instance() or QApplication([])


class _NoStep(BasePage):
    def __init__(self):
        super(_NoStep, self).__init__(None, "T", "d")

    def build_body(self, layout):
        self.a = QLabel("A"); layout.addWidget(self.a)


class _StepPage(BasePage):
    def __init__(self):
        super(_StepPage, self).__init__(None, "T", "d")

    def build_body(self, layout):
        self.a = QLabel("A"); layout.addWidget(self.a)
        self.b = QLabel("B"); layout.addWidget(self.b)

    def guide_steps(self):
        return [(None, "开场", "介绍"),
                (self.a, "第一处", "放 A"),
                (self.b, "第二处", "放 B")]


class TestGuideButton(unittest.TestCase):
    def test_no_steps_hides_button(self):
        p = _NoStep()
        self.assertIsNone(getattr(p, "_guide_btn", None))

    def test_steps_show_button(self):
        p = _StepPage()
        self.assertIsNotNone(p._guide_btn)
        self.assertEqual(p._guide_btn.text(), "使用指引")


class TestGuideOverlay(unittest.TestCase):
    def setUp(self):
        self.p = _StepPage()
        self.p.resize(900, 640)

    def test_start_and_advance(self):
        self.p.start_guide()
        ov = self.p._guide
        self.assertIsInstance(ov, GuideOverlay)
        self.assertEqual(ov._idx, 0)
        ov.next()
        self.assertEqual(ov._idx, 1)
        ov.next()
        self.assertEqual(ov._idx, 2)
        ov.prev()
        self.assertEqual(ov._idx, 1)

    def test_finish_hides(self):
        self.p.start_guide()
        ov = self.p._guide
        fired = []
        ov.finished.connect(lambda: fired.append(1))
        ov._goto(2)                 # 跳到末步
        ov.next()                   # 末步再下一步 = 完成
        self.assertTrue(fired)
        self.assertTrue(ov.isHidden())

    def test_rect_of_none_is_empty(self):
        self.p.start_guide()
        ov = self.p._guide
        self.assertTrue(ov._rect_of(None).isEmpty())
        # 真实控件应给出非空高亮矩形
        self.assertFalse(ov._rect_of(self.p.a).isEmpty())


class TestDeliveryGuide(unittest.TestCase):
    def test_delivery_steps_cover_controls(self):
        from ui.pages.delivery_page import DeliveryPage
        pg = DeliveryPage(None)
        steps = pg.guide_steps()
        self.assertGreaterEqual(len(steps), 6)
        widgets = [w for w, _, _ in steps if w is not None]
        for z in (pg.z_list, pg.z_sup, pg.z_ref, pg._ot_card, pg.panel):
            self.assertIn(z, widgets)


# 所有已接引导的功能页 -> (模块, 类名)。about/home/settings 按设计不接。
_GUIDED_PAGES = [
    ("delivery_page", "DeliveryPage"), ("attendance_page", "AttendancePage"),
    ("reconcile_page", "ReconcilePage"), ("arrival_page", "ArrivalPage"),
    ("pivot_page", "PivotPage"), ("purchase_page", "PurchasePage"),
    ("compare_page", "ComparePage"), ("invoice_page", "InvoicePage"),
    ("currency_page", "CurrencyPage"), ("rename_page", "RenamePage"),
    ("text_page", "TextPage"), ("pdf_page", "PdfPage"),
    ("excel_tools_page", "ExcelToolsPage"), ("library_page", "LibraryPage"),
]


class TestAllPagesGuide(unittest.TestCase):
    def test_every_guided_page_wellformed(self):
        import importlib
        for mod, cls in _GUIDED_PAGES:
            m = importlib.import_module("ui.pages." + mod)
            pg = getattr(m, cls)(None)
            steps = pg.guide_steps()
            self.assertGreaterEqual(len(steps), 3, "%s 步骤过少" % cls)
            # 每步:控件为 None 或真实 QWidget;标题/说明非空
            from PySide2.QtWidgets import QWidget
            for w, title, body in steps:
                self.assertTrue(w is None or isinstance(w, QWidget), "%s 控件非法" % cls)
                self.assertTrue(title and body, "%s 有空文案" % cls)
            # 有步骤 -> 应显示指引按钮
            self.assertIsNotNone(pg._guide_btn, "%s 未显示指引按钮" % cls)

    def test_landing_pages_have_no_guide(self):
        import importlib
        from unittest import mock
        for mod, cls in [("home_page", "HomePage"), ("settings_page", "SettingsPage"),
                         ("about_page", "AboutPage")]:
            m = importlib.import_module("ui.pages." + mod)
            pg = getattr(m, cls)(mock.MagicMock())    # 这些页构建期会用到 main.*
            self.assertEqual(pg.guide_steps(), [])
            self.assertIsNone(getattr(pg, "_guide_btn", None), "%s 不应有指引按钮" % cls)


if __name__ == "__main__":
    unittest.main()
