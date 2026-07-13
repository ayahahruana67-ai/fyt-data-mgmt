# -*- coding: utf-8 -*-
"""
后台工作线程 —— 在子线程跑 core.run，避免界面卡死
==================================================
Qt 界面不是线程安全的：core 在子线程运行，日志/结果通过信号回主线程。
兼容 Windows 7 + Python 3.8 + PySide2。
"""
import inspect
import traceback

from PySide2.QtCore import QThread, Signal


class Worker(QThread):
    """通用工作线程：把一个可调用 fn(log=..., [progress=...]) 放到子线程执行。

    fn 若接受 progress 形参，会额外收到进度回调（0~100），供进度条使用；
    不接受则只传 log，保持对旧调用的兼容。
    """
    sig_log = Signal(str)          # 一行日志
    sig_progress = Signal(int)     # 进度百分比 0~100
    sig_done = Signal(object)      # 成功，携带结果 dict
    sig_error = Signal(str, str)   # 失败：(简要信息, 完整堆栈)

    def __init__(self, fn, parent=None):
        super(Worker, self).__init__(parent)
        self._fn = fn

    def run(self):
        try:
            kwargs = {"log": self._emit_log}
            try:
                if "progress" in inspect.signature(self._fn).parameters:
                    kwargs["progress"] = self._emit_progress
            except (TypeError, ValueError):
                pass
            result = self._fn(**kwargs)
            self.sig_done.emit(result)
        except Exception as e:
            self.sig_error.emit(str(e), traceback.format_exc())

    def _emit_log(self, msg):
        self.sig_log.emit(str(msg))

    def _emit_progress(self, pct):
        self.sig_progress.emit(int(pct))
