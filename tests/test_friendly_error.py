# -*- coding: utf-8 -*-
"""BasePage._friendly_error 异常翻译的单测(offscreen)。

钉死:底层系统异常(占用/找不到/损坏/磁盘满/内存不足)被翻成客户能懂的中文;
已是友好中文的业务异常走默认分支加前缀、不被误伤。
"""
import os
import unittest
import warnings

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
warnings.filterwarnings("ignore")

from PySide2.QtWidgets import QApplication

from ui.pages.base_page import BasePage

_app = QApplication.instance() or QApplication([])


class _Page(BasePage):
    def __init__(self):
        super(_Page, self).__init__(None, "T", "d")

    def build_body(self, layout):
        pass


class TestFriendlyError(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = _Page()

    def f(self, msg):
        return self.page._friendly_error(msg)

    def test_permission(self):
        self.assertIn("占用", self.f("[Errno 13] Permission denied: 'x.xlsx'"))
        self.assertIn("占用", self.f("另一个程序正在使用此文件"))

    def test_not_found(self):
        self.assertIn("找不到", self.f("No such file or directory"))
        self.assertIn("找不到", self.f("系统找不到指定的文件"))

    def test_corrupt(self):
        self.assertIn("损坏", self.f("File is not a zip file"))
        self.assertIn("损坏", self.f("BadZipFile"))

    def test_disk_full(self):
        self.assertIn("磁盘空间", self.f("[Errno 28] No space left on device"))
        self.assertIn("磁盘空间", self.f("磁盘空间不足"))

    def test_out_of_memory(self):
        self.assertIn("内存", self.f("MemoryError"))
        self.assertIn("内存", self.f("Unable to allocate memory"))

    def test_business_message_passthrough(self):
        # core 已给的友好中文不该被前几条误命中,走默认分支加前缀
        msg = "未能识别表头，请检查表头行"
        out = self.f(msg)
        self.assertIn("未能识别表头", out)
        self.assertTrue(out.startswith("处理时遇到问题"))

    def test_none_message(self):
        self.assertIn("未知错误", self.f(None))


if __name__ == "__main__":
    unittest.main()
