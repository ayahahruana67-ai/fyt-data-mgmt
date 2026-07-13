# -*- coding: utf-8 -*-
"""
主窗口 —— 侧栏导航 + 堆叠页面(带切换动画) + 功能分类
====================================================
功能按"考勤管理 / 数据处理"分组，另有设置、关于。为将来新增功能预留插槽
（在 NAV 列表加一项 + 一个页面即可）。
兼容 Windows 7 + Python 3.8 + PySide2。
"""
from PySide2.QtCore import (Qt, QPropertyAnimation, QEasingCurve, QTimer,
                            QParallelAnimationGroup, QPoint)
from PySide2.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QLabel, QPushButton, QStackedWidget, QApplication,
                               QButtonGroup, QGraphicsOpacityEffect)

from . import theme
from .pages.home_page import HomePage
from .pages.attendance_page import AttendancePage
from .pages.reconcile_page import ReconcilePage
from .pages.arrival_page import ArrivalPage
from .pages.pivot_page import PivotPage
from .pages.library_page import LibraryPage
from .pages.settings_page import SettingsPage
from .pages.about_page import AboutPage
from core import version, settings as settings_mod


# 导航定义：(分组, 标题, 页面键)；分组为 None 表示单列在底部
NAV = [
    ("", "首页", "home"),
    ("考勤管理", "考勤数据填报", "attendance"),
    ("考勤管理", "工时对账", "reconcile"),
    ("数据处理", "到料明细表", "arrival"),
    ("数据处理", "透视表制作", "pivot"),
    ("数据", "数据库", "library"),
    ("系统", "设置", "settings"),
    ("系统", "关于 / 更新", "about"),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle(version.full_title())
        self.resize(1040, 720)
        self.setMinimumSize(880, 600)
        self.settings = settings_mod.get_settings()
        self._pages = {}
        self._nav_btns = {}
        self._build()
        self.switch_to("home")
        QTimer.singleShot(300, self._maybe_onboard)

    def _build(self):
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        lay = QHBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_sidebar())
        lay.addWidget(self._build_stack(), 1)

    def _build_sidebar(self):
        bar = QWidget()
        bar.setObjectName("Sidebar")
        bar.setFixedWidth(210)
        v = QVBoxLayout(bar)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        brand = QLabel("峰运通")
        brand.setObjectName("Brand")
        v.addWidget(brand)
        sub = QLabel("数据管理系统  " + version.version_str())
        sub.setObjectName("BrandSub")
        v.addWidget(sub)

        self._grp = QButtonGroup(self)
        self._grp.setExclusive(True)
        last_group = None
        for group, title, key in NAV:
            if group != last_group:
                if group:                      # 空分组名(如首页)不画分组标题
                    gl = QLabel(group)
                    gl.setObjectName("NavGroup")
                    v.addWidget(gl)
                last_group = group
            b = QPushButton(title)
            b.setObjectName("NavBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.switch_to(k))
            self._grp.addButton(b)
            self._nav_btns[key] = b
            v.addWidget(b)
        v.addStretch(1)
        tip = QLabel("兼容 Win7 · Python 3.8")
        tip.setObjectName("BrandSub")
        v.addWidget(tip)
        return bar

    def _build_stack(self):
        self.stack = QStackedWidget()
        ctors = {"home": HomePage, "attendance": AttendancePage,
                 "reconcile": ReconcilePage, "arrival": ArrivalPage,
                 "pivot": PivotPage, "library": LibraryPage,
                 "settings": SettingsPage, "about": AboutPage}
        for _, _, key in NAV:
            page = ctors[key](self)
            self._pages[key] = page
            self.stack.addWidget(page)
        return self.stack

    def switch_to(self, key):
        page = self._pages.get(key)
        if page is None:
            return
        if self._nav_btns.get(key):
            self._nav_btns[key].setChecked(True)
        # 进入首页/数据库时刷新其数据库统计与列表
        fn = getattr(page, "refresh_view", None)
        if callable(fn):
            fn()
        self.stack.setCurrentWidget(page)
        self._fade_in(page)

    def _fade_in(self, widget):
        """页面切换动画：淡入 + 轻微上滑。"""
        eff = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(eff)
        fade = QPropertyAnimation(eff, b"opacity", self)
        fade.setDuration(240)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)

        start_pos = widget.pos() + QPoint(0, 14)
        end_pos = widget.pos()
        slide = QPropertyAnimation(widget, b"pos", self)
        slide.setDuration(300)
        slide.setStartValue(start_pos)
        slide.setEndValue(end_pos)
        slide.setEasingCurve(QEasingCurve.OutCubic)

        grp = QParallelAnimationGroup(self)
        grp.addAnimation(fade)
        grp.addAnimation(slide)
        grp.finished.connect(lambda: widget.setGraphicsEffect(None))
        grp.start()
        self._anim = grp   # 防止被 GC

    # ---------- 主题实时切换 ----------
    def apply_theme(self, mode):
        """切换主题模式并即时重贴样式表；动态属性会随之重新生效。"""
        theme.set_mode(mode)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(theme.stylesheet())
        # 重贴样式表后，个别缓存了内联样式的部件让其重读配色
        for page in self._pages.values():
            fn = getattr(page, "on_theme_changed", None)
            if callable(fn):
                fn()

    # ---------- 页面联动 ----------
    def send_to_reconcile(self, paths):
        """考勤填报结果 -> 工时对账 的"数据来源"。"""
        self._pages["reconcile"].add_source_files(paths)
        self.switch_to("reconcile")

    def send_to_pivot(self, paths):
        """到料/其它 -> 透视表 来源（预留联动）。"""
        self._pages["pivot"].add_source_files(paths)
        self.switch_to("pivot")

    def _maybe_onboard(self):
        if not self.settings.get("onboarding_seen", False):
            from .dialogs.onboarding import OnboardingDialog
            dlg = OnboardingDialog(self)
            dlg.exec_()
            self.settings.set("onboarding_seen", True)
            self.settings.save()
