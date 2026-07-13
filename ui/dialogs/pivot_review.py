# -*- coding: utf-8 -*-
"""
透视表人工复核对话框
====================
展示 analyze 得到的决策点，让用户确认：
  · 每个工作表是否纳入（附识别类型/可信度/原因）；
  · 被判为"疑似真实但会删除"的行是否保留；
  · 单位冲突 / 规格合并 的提示（只读，供知情）。
返回 choices，喂给 pivot_core.run。
兼容 Windows 7 + Python 3.8 + PySide2。
"""
from PySide2.QtCore import Qt
from PySide2.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QTabWidget, QWidget, QTableWidget, QTableWidgetItem,
                               QHeaderView, QCheckBox, QAbstractItemView)

from .. import theme


class PivotReviewDialog(QDialog):
    def __init__(self, plan, parent=None):
        super(PivotReviewDialog, self).__init__(parent)
        self.plan = plan
        self.setWindowTitle("人工复核 —— 透视表制作")
        self.setModal(True)
        self.resize(760, 560)
        self.setStyleSheet(theme.stylesheet())
        self._sheet_cbs = {}     # id -> QCheckBox
        self._held_cbs = {}      # (sid, ridx) -> QCheckBox
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(12)
        head = QLabel("请确认下列决策点。默认与全自动一致，可按需调整后再生成。")
        head.setObjectName("PageDesc"); head.setWordWrap(True)
        lay.addWidget(head)

        tabs = QTabWidget()
        tabs.addTab(self._sheets_tab(), "工作表纳入 (%d)" % len(self.plan["sheets"]))
        tabs.addTab(self._held_tab(), "疑似误删行 (%d)" % len(self.plan.get("held_index", [])))
        tabs.addTab(self._conflict_tab(), "单位/规格提示")
        lay.addWidget(tabs, 1)

        row = QHBoxLayout()
        row.addStretch(1)
        cancel = QPushButton("取消"); cancel.setObjectName("Ghost"); cancel.clicked.connect(self.reject)
        ok = QPushButton("按此生成"); ok.setObjectName("Primary"); ok.clicked.connect(self.accept)
        row.addWidget(cancel); row.addWidget(ok)
        lay.addLayout(row)

    def _sheets_tab(self):
        w = QWidget(); v = QVBoxLayout(w)
        tb = QTableWidget(len(self.plan["sheets"]), 5)
        tb.setHorizontalHeaderLabels(["纳入", "文件", "工作表", "识别类型", "可信度"])
        tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tb.verticalHeader().setVisible(False)
        hh = tb.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        for r, s in enumerate(self.plan["sheets"]):
            cb = QCheckBox(); cb.setChecked(bool(s["use"]))
            self._sheet_cbs[s["id"]] = cb
            holder = QWidget(); hl = QHBoxLayout(holder)
            hl.setContentsMargins(0, 0, 0, 0); hl.setAlignment(Qt.AlignCenter); hl.addWidget(cb)
            tb.setCellWidget(r, 0, holder)
            tb.setItem(r, 1, QTableWidgetItem(s["file"]))
            it2 = QTableWidgetItem(s["sheet"]); it2.setToolTip(s.get("reason", ""))
            tb.setItem(r, 2, it2)
            tb.setItem(r, 3, QTableWidgetItem(s["kind"]))
            conf = QTableWidgetItem(str(s["confidence"]))
            if s["confidence"] < 60:
                conf.setForeground(Qt.red)
            tb.setItem(r, 4, conf)
        v.addWidget(tb)
        return w

    def _held_tab(self):
        w = QWidget(); v = QVBoxLayout(w)
        held = self.plan.get("held_index", [])
        if not held:
            lbl = QLabel("没有疑似误删的行。数据很干净，直接生成即可。")
            lbl.setObjectName("Hint"); v.addWidget(lbl); v.addStretch(1); return w
        info = QLabel("以下行被规则判为可能应删除，但疑似真实数据。勾选=保留进入汇总。")
        info.setObjectName("Hint"); info.setWordWrap(True); v.addWidget(info)
        tb = QTableWidget(len(held), 3)
        tb.setHorizontalHeaderLabels(["保留", "来源", "内容摘要"])
        tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tb.verticalHeader().setVisible(False)
        tb.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for r, h in enumerate(held):
            cb = QCheckBox(); self._held_cbs[(h["sid"], h["ridx"])] = cb
            holder = QWidget(); hl = QHBoxLayout(holder)
            hl.setContentsMargins(0, 0, 0, 0); hl.setAlignment(Qt.AlignCenter); hl.addWidget(cb)
            tb.setCellWidget(r, 0, holder)
            tb.setItem(r, 1, QTableWidgetItem(str(h.get("sheet", ""))))
            tb.setItem(r, 2, QTableWidgetItem(str(h.get("summary", h.get("rec", "")))))
        v.addWidget(tb)
        return w

    def _conflict_tab(self):
        w = QWidget(); v = QVBoxLayout(w)
        uc = self.plan.get("unit_conflicts", [])
        sm = self.plan.get("spec_merges", [])
        if not uc and not sm:
            lbl = QLabel("没有单位冲突或规格合并需要关注。")
            lbl.setObjectName("Hint"); v.addWidget(lbl); v.addStretch(1); return w
        if uc:
            v.addWidget(self._sec("单位冲突（同物料出现多种单位，已按多数原则统一）",
                                  [str(x) for x in uc]))
        if sm:
            v.addWidget(self._sec("规格合并（相近规格已归并）", [str(x) for x in sm]))
        v.addStretch(1)
        return w

    def _sec(self, title, lines):
        box = QWidget(); bv = QVBoxLayout(box)
        t = QLabel(title); t.setObjectName("SecTitle"); bv.addWidget(t)
        for ln in lines[:200]:
            l = QLabel("· " + ln); l.setObjectName("Hint"); l.setWordWrap(True); bv.addWidget(l)
        return box

    def choices(self):
        from core import pivot_core
        ch = pivot_core._default_choices(self.plan)
        for sid, cb in self._sheet_cbs.items():
            ch["sheets"][sid] = cb.isChecked()
        for key, cb in self._held_cbs.items():
            ch["held"][key] = cb.isChecked()
        return ch
