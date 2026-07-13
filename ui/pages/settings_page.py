# -*- coding: utf-8 -*-
"""设置页。统一输出位置(解决混乱点) + 启动检查更新 + 打开数据目录。"""
import os

from PySide2.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                               QRadioButton, QButtonGroup, QLineEdit, QPushButton,
                               QFileDialog, QCheckBox)

from .base_page import BasePage
from core import settings as settings_mod, paths, version


class SettingsPage(BasePage):
    def __init__(self, main):
        self.settings = settings_mod.get_settings()
        super(SettingsPage, self).__init__(
            main, "设置", "统一管理四个功能的输出位置与系统选项。改动即时生效。")

    def build_body(self, layout):
        # ---- 输出位置 ----
        card = QFrame(); card.setObjectName("Card")
        v = QVBoxLayout(card); v.setContentsMargins(16, 14, 16, 14); v.setSpacing(8)
        t = QLabel("输出位置"); t.setObjectName("SecTitle"); v.addWidget(t)
        h = QLabel("四个功能的处理结果统一按此规则存放，按“功能/时间戳”归档。")
        h.setObjectName("Hint"); h.setWordWrap(True); v.addWidget(h)

        self.grp = QButtonGroup(self)
        self.rb_unified = QRadioButton("文档下统一文件夹（推荐）")
        self.rb_beside = QRadioButton("源文件旁的 output 文件夹")
        self.rb_custom = QRadioButton("自定义文件夹")
        for i, rb in enumerate((self.rb_unified, self.rb_beside, self.rb_custom)):
            self.grp.addButton(rb, i); v.addWidget(rb)
            rb.toggled.connect(self._on_mode)

        self.lbl_unified = QLabel("→ " + paths.default_output_root())
        self.lbl_unified.setObjectName("Hint"); v.addWidget(self.lbl_unified)

        row = QHBoxLayout()
        self.ed_custom = QLineEdit(self.settings.custom_output_root)
        self.ed_custom.setPlaceholderText("选择一个自定义输出根目录…")
        btn = QPushButton("浏览…"); btn.setObjectName("Mini"); btn.clicked.connect(self._pick)
        row.addWidget(self.ed_custom, 1); row.addWidget(btn)
        v.addLayout(row)
        layout.addWidget(card)

        # ---- 外观 ----
        card_a = QFrame(); card_a.setObjectName("Card")
        va = QVBoxLayout(card_a); va.setContentsMargins(16, 14, 16, 14); va.setSpacing(8)
        ta = QLabel("外观"); ta.setObjectName("SecTitle"); va.addWidget(ta)
        ha = QLabel("选择界面主题。“跟随系统”会自动匹配 Windows 的浅色/深色设置。")
        ha.setObjectName("Hint"); ha.setWordWrap(True); va.addWidget(ha)
        self.grp_theme = QButtonGroup(self)
        self.rb_auto = QRadioButton("跟随系统（推荐）")
        self.rb_light = QRadioButton("浅色")
        self.rb_dark = QRadioButton("深色")
        theme_row = QHBoxLayout(); theme_row.setSpacing(18)
        for rb in (self.rb_auto, self.rb_light, self.rb_dark):
            self.grp_theme.addButton(rb); theme_row.addWidget(rb)
            rb.toggled.connect(self._on_theme)
        theme_row.addStretch(1)
        va.addLayout(theme_row)
        layout.addWidget(card_a)

        # ---- 系统 ----
        card2 = QFrame(); card2.setObjectName("Card")
        v2 = QVBoxLayout(card2); v2.setContentsMargins(16, 14, 16, 14); v2.setSpacing(8)
        t2 = QLabel("系统"); t2.setObjectName("SecTitle"); v2.addWidget(t2)
        self.cb_update = QCheckBox("启动时自动检查更新")
        self.cb_update.setChecked(bool(self.settings.get("check_update_on_start", False)))
        self.cb_update.toggled.connect(self._on_update_toggle)
        v2.addWidget(self.cb_update)
        r2 = QHBoxLayout()
        b_data = QPushButton("打开数据目录"); b_data.setObjectName("Ghost")
        b_data.clicked.connect(lambda: self._open(paths.app_data_dir()))
        b_out = QPushButton("打开输出根目录"); b_out.setObjectName("Ghost")
        b_out.clicked.connect(lambda: self._open(paths.default_output_root()))
        r2.addWidget(b_data); r2.addWidget(b_out); r2.addStretch(1)
        v2.addLayout(r2)
        layout.addWidget(card2)
        layout.addStretch(1)

        self._load()

    def _load(self):
        mode = self.settings.output_mode
        {"unified": self.rb_unified, "beside": self.rb_beside,
         "custom": self.rb_custom}.get(mode, self.rb_unified).setChecked(True)
        self.ed_custom.setEnabled(mode == "custom")
        tmode = self.settings.theme_mode
        {"auto": self.rb_auto, "light": self.rb_light,
         "dark": self.rb_dark}.get(tmode, self.rb_auto).setChecked(True)

    def _on_theme(self, *_):
        if not any((self.rb_auto.isChecked(), self.rb_light.isChecked(),
                    self.rb_dark.isChecked())):
            return
        mode = ("auto" if self.rb_auto.isChecked()
                else "light" if self.rb_light.isChecked() else "dark")
        if mode == self.settings.theme_mode:
            return
        self.settings.set("theme_mode", mode)
        self.settings.save()
        self.main.apply_theme(mode)      # 实时换肤

    def _on_mode(self, *_):
        if self.rb_unified.isChecked(): mode = "unified"
        elif self.rb_beside.isChecked(): mode = "beside"
        else: mode = "custom"
        self.ed_custom.setEnabled(mode == "custom")
        self.settings.set("output_mode", mode)
        self.settings.save()

    def _pick(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出根目录", self.ed_custom.text() or "")
        if d:
            self.ed_custom.setText(d)
            self.settings.set("custom_output_root", d)
            self.rb_custom.setChecked(True)
            self.settings.save()

    def _on_update_toggle(self, on):
        self.settings.set("check_update_on_start", bool(on))
        self.settings.save()

    def _open(self, d):
        try:
            if d and os.path.isdir(d):
                os.startfile(d)
        except Exception:
            pass
