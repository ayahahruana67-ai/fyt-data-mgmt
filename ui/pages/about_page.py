# -*- coding: utf-8 -*-
"""关于 / 更新页。显示版本信息，检查更新（更新源未配置时给出说明）。"""
from PySide2.QtCore import Qt, QTimer
from PySide2.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QProgressBar, QApplication, QMessageBox)

from .base_page import BasePage
from ..worker import Worker
from core import version, updater


class AboutPage(BasePage):
    def __init__(self, main):
        super(AboutPage, self).__init__(main, "关于 / 更新", "版本信息与在线更新。")

    def build_body(self, layout):
        card = QFrame(); card.setObjectName("Card")
        v = QVBoxLayout(card); v.setContentsMargins(20, 18, 20, 18); v.setSpacing(6)
        name = QLabel(version.APP_NAME); name.setStyleSheet("font-size:18px; font-weight:bold;")
        v.addWidget(name)
        v.addWidget(self._kv("版本", version.version_str()))
        v.addWidget(self._kv("构建日期", version.BUILD_DATE))
        v.addWidget(self._kv("发布方", version.PUBLISHER))
        v.addWidget(self._kv("运行环境", "Windows 7+ · Python 3.8 · PySide2"))
        feats = QLabel("集成功能：考勤填报 · 工时对账 · 到料明细 · 透视表制作")
        feats.setObjectName("Hint"); feats.setWordWrap(True); v.addWidget(feats)
        layout.addWidget(card)

        card2 = QFrame(); card2.setObjectName("Card")
        v2 = QVBoxLayout(card2); v2.setContentsMargins(20, 16, 20, 16); v2.setSpacing(8)
        t = QLabel("在线更新"); t.setObjectName("SecTitle"); v2.addWidget(t)
        self.status = QLabel(); self.status.setObjectName("Hint"); self.status.setWordWrap(True)
        v2.addWidget(self.status)
        self.bar = QProgressBar(); self.bar.setRange(0, 100); self.bar.setVisible(False)
        v2.addWidget(self.bar)
        row = QHBoxLayout()
        self.btn = QPushButton("检查更新"); self.btn.setObjectName("Primary")
        self.btn.clicked.connect(self._on_button)
        row.addWidget(self.btn); row.addStretch(1)
        v2.addLayout(row)
        layout.addWidget(card2)
        layout.addStretch(1)
        self._pending = None        # 待安装的新版信息（检查到更新后暂存）
        self._refresh_update_status()

    def _kv(self, k, val):
        w = QLabel("%s：%s" % (k, val)); w.setObjectName("PageDesc"); return w

    def _refresh_update_status(self):
        if updater.is_configured():
            self.status.setText("已配置更新源，可点击检查是否有新版本。")
            self.btn.setEnabled(True)
        else:
            self.status.setText("更新源尚未配置。仓库建立后，在 core/version.py 填入 "
                                "GITHUB_OWNER/GITHUB_REPO 或 UPDATE_MANIFEST_URL 即可启用在线更新。")
            self.btn.setEnabled(False)

    def _on_button(self):
        """一个按钮两种角色：无待装版本=检查更新；有=下载并安装。"""
        if self._pending:
            self._download_and_install()
        else:
            self._check()

    def _check(self):
        self.btn.setEnabled(False)
        self.status.setText("正在检查…")
        w = Worker(lambda log=None: updater.check_update())
        w.sig_done.connect(self._on_result)
        w.sig_error.connect(lambda m, tb: self._on_result({"status": "error", "msg": m}))
        self._w = w
        w.start()

    def _on_result(self, res):
        self.btn.setEnabled(True)
        self._pending = None
        self.btn.setText("检查更新")
        if not res:
            self.status.setText("更新源未配置。")
        elif res.get("status") == "latest":
            self.status.setText("已是最新版本（%s）。" % version.version_str())
        elif res.get("status") == "update":
            if not res.get("url"):
                self.status.setText("发现新版本 v%s，但更新清单未提供下载地址，请联系管理员。"
                                    % res.get("version"))
                return
            self._pending = res
            self.btn.setText("下载并安装 v%s" % res.get("version"))
            notes = res.get("notes", "") or "（无更新说明）"
            self.status.setText("发现新版本 v%s：\n%s" % (res.get("version"), notes))
        else:
            self.status.setText("检查失败：%s\n请检查网络后重试。" % res.get("msg", "网络错误"))

    def _download_and_install(self):
        res = self._pending
        self.btn.setEnabled(False)
        self.bar.setValue(0); self.bar.setVisible(True)
        self.status.setText("正在下载安装包…")
        url = res.get("url")
        w = Worker(lambda log=None, progress=None:
                   updater.download_installer(url, progress=progress, log=log))
        w.sig_progress.connect(self.bar.setValue)
        w.sig_log.connect(self.status.setText)
        w.sig_done.connect(self._on_downloaded)
        w.sig_error.connect(self._on_download_error)
        self._w = w
        w.start()

    def _on_download_error(self, msg, tb):
        self.bar.setVisible(False)
        self.btn.setEnabled(True)
        self.status.setText("下载失败：%s\n可稍后重试，或联系管理员手动更新。" % msg)

    def _on_downloaded(self, path):
        self.bar.setValue(100)
        self.status.setText("下载完成，即将启动安装向导。\n程序会自动退出，请按向导完成安装后重新打开。")
        ret = QMessageBox.information(
            self, "开始安装",
            "安装包已下载完成，点击「确定」后将启动安装向导，本程序会自动关闭。\n"
            "（安装过程可能弹出系统权限提示，请选择「是」。）",
            QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)
        if ret != QMessageBox.Ok:
            self.btn.setEnabled(True)
            self.status.setText("已取消安装。安装包已下载至临时目录，可稍后再装。")
            return
        try:
            updater.run_installer(path)
        except Exception as e:
            self.btn.setEnabled(True)
            self.status.setText("启动安装程序失败：%s" % e)
            return
        # 延迟退出，给安装器起进程的时间，随后释放旧文件占用
        QTimer.singleShot(800, QApplication.quit)
