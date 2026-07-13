# -*- coding: utf-8 -*-
"""
一键打包 —— 峰运通数据管理系统
================================
步骤：
  1) 由 version.py 生成 exe 版本资源；
  2) PyInstaller 按 packaging/app.spec 打出 dist/FYTDataMgmt/（单目录）；
  3) 若检测到 Inno Setup(ISCC.exe)，编译出中文安装向导到 dist/installer/。
未装 Inno 时，跳过第 3 步并打印安装指引，绿色版(dist 目录)已可直接用。

用法：  python build.py            # 完整流程
        python build.py --no-installer
兼容 Windows 7 + Python 3.8。
"""
import os
import sys
import glob
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from core import version as V   # noqa: E402

PKG = os.path.join(HERE, "packaging")
DIST_APP = os.path.join(HERE, "dist", V.APP_ID)
INSTALLER_OUT = os.path.join(HERE, "dist", "installer")


def _run(cmd, **kw):
    print(">>", " ".join(cmd))
    return subprocess.call(cmd, **kw)


def step_pyinstaller():
    print("\n=== [1/3] 生成版本资源 ===")
    sys.path.insert(0, PKG)
    import make_version_info
    make_version_info.write()
    print("\n=== [2/3] PyInstaller 打包 ===")
    code = _run([sys.executable, "-m", "PyInstaller",
                 os.path.join(PKG, "app.spec"),
                 "--noconfirm", "--clean",
                 "--distpath", os.path.join(HERE, "dist"),
                 "--workpath", os.path.join(HERE, "build", "pyi")],
                cwd=HERE)
    if code != 0:
        raise SystemExit("PyInstaller 失败，错误码 %d" % code)
    exe = os.path.join(DIST_APP, V.APP_ID + ".exe")
    if not os.path.exists(exe):
        raise SystemExit("未找到生成的 exe：%s" % exe)
    print("[完成] 绿色版已生成：", DIST_APP)
    return exe


def find_iscc():
    """按常见位置定位 Inno Setup 编译器 ISCC.exe。"""
    exe = shutil.which("iscc") or shutil.which("ISCC")
    if exe:
        return exe
    local = os.environ.get("LOCALAPPDATA", "")
    roots = [os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
             os.environ.get("ProgramFiles", r"C:\Program Files"),
             os.path.join(local, "Programs") if local else ""]
    for r in roots:
        for ver in ("Inno Setup 6", "Inno Setup 5"):
            p = os.path.join(r or "", ver, "ISCC.exe")
            if os.path.exists(p):
                return p
    return None


def find_chinese_isl(iscc_path):
    """在 Inno 安装目录的 Languages 下找简体中文语言文件。"""
    base = os.path.dirname(iscc_path)
    for name in ("ChineseSimplified.isl", "ChineseSimp.isl"):
        for cand in (os.path.join(base, "Languages", name),
                     os.path.join(base, name)):
            if os.path.exists(cand):
                return cand
    return None


def step_installer():
    print("\n=== [3/3] Inno Setup 制作安装向导 ===")
    iscc = find_iscc()
    if not iscc:
        print("! 未检测到 Inno Setup(ISCC.exe)。已跳过安装包制作。")
        print("  安装向导制作方法：")
        print("   1. 到 https://jrsoftware.org/isdl.php 下载并安装 Inno Setup 6；")
        print("   2. 重新运行  python build.py  即可自动生成安装包；")
        print("   3. 或手动编译： ISCC.exe packaging\installer.iss")
        print("  当前 dist\%s 已是可直接分发的绿色版。" % V.APP_ID)
        return None
    if not os.path.isdir(DIST_APP):
        raise SystemExit("缺少打包产物 %s，请先完成第 2 步。" % DIST_APP)
    if not os.path.isdir(INSTALLER_OUT):
        os.makedirs(INSTALLER_OUT)
    defines = ["/DMyAppVersion=%s" % V.VERSION, "/DMyAppName=%s" % V.APP_NAME,
               "/DMyAppId=%s" % V.APP_ID, "/DMyAppPublisher=%s" % V.PUBLISHER,
               "/DMyAppExe=%s.exe" % V.APP_ID]
    cn = find_chinese_isl(iscc)
    if cn:
        defines.append("/DChineseIsl=%s" % cn)
        print("· 使用简体中文安装向导：", cn)
    else:
        print("· 未找到简体中文语言文件，安装向导将用英文界面(程序本身仍是中文)。")
    code = _run([iscc] + defines + [os.path.join(PKG, "installer.iss")], cwd=HERE)
    if code != 0:
        raise SystemExit("Inno Setup 编译失败，错误码 %d" % code)
    setups = sorted(glob.glob(os.path.join(INSTALLER_OUT, "*.exe")),
                    key=os.path.getmtime, reverse=True)
    if setups:
        print("[完成] 安装包已生成：", setups[0])
        return setups[0]
    return None


def main():
    make_installer = "--no-installer" not in sys.argv
    step_pyinstaller()
    if make_installer:
        step_installer()
    print("\n全部完成。")


if __name__ == "__main__":
    main()
