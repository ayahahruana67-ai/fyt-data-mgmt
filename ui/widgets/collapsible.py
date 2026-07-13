# -*- coding: utf-8 -*-
"""Collapsible —— 可折叠段落（标题按钮 + 富文本内容），用于帮助文档。"""
from PySide2.QtCore import Qt
from PySide2.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel


class Collapsible(QFrame):
    def __init__(self, title, html, expanded=False, parent=None):
        super(Collapsible, self).__init__(parent)
        self.setObjectName("Collapsible")
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self._title = title
        self.btn = QPushButton(("▾  " if expanded else "▸  ") + title)
        self.btn.setObjectName("CollapseHead")
        self.btn.setCheckable(True)
        self.btn.setChecked(expanded)
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.clicked.connect(self._toggle)
        v.addWidget(self.btn)

        self.body = QLabel(html)
        self.body.setObjectName("CollapseBody")
        self.body.setWordWrap(True)
        self.body.setTextFormat(Qt.RichText)
        self.body.setOpenExternalLinks(True)
        self.body.setVisible(expanded)
        v.addWidget(self.body)

    def _toggle(self):
        on = self.btn.isChecked()
        self.btn.setText(("▾  " if on else "▸  ") + self._title)
        self.body.setVisible(on)
