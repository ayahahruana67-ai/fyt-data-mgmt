# -*- coding: utf-8 -*-
"""ClickableCard —— 首页快捷入口卡片（整卡可点，含图标/标题/说明）。"""
from PySide2.QtCore import Qt, Signal
from PySide2.QtWidgets import QFrame, QVBoxLayout, QLabel


class ClickableCard(QFrame):
    clicked = Signal(str)

    def __init__(self, key, icon, title, desc, parent=None):
        super(ClickableCard, self).__init__(parent)
        self.setObjectName("EntryCard")
        self._key = key
        self.setCursor(Qt.PointingHandCursor)
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(6)
        ic = QLabel(icon); ic.setObjectName("EntryIcon")
        v.addWidget(ic)
        t = QLabel(title); t.setObjectName("EntryTitle")
        v.addWidget(t)
        d = QLabel(desc); d.setObjectName("EntryDesc")
        d.setWordWrap(True)
        v.addWidget(d, 1)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.pos()):
            self.clicked.emit(self._key)
        super(ClickableCard, self).mouseReleaseEvent(e)
