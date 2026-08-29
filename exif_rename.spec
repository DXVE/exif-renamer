# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec: 主程序 rename_tool.py
产物名: rename_tool-<BUILD_TS>.exe (跟随原脚本名)
BUILD_TS 由 GitHub Actions 通过 env WM_BUILD_TAG 传入
"""
import os

WM_BUILD_TAG = os.environ.get('WM_BUILD_TAG', 'dev')


def build_exe(entry):
    # 产物名默认用 entry 脚本的 basename (不带 .py)
    name = os.path.splitext(os.path.basename(entry))[0]
    a = Analysis(
        [entry],
        pathex=[],
        binaries=[],
        datas=[('assets/icon.ico', '.'), ('assets/icon.png', '.')],   # ico 给 EXE 资源, png 给源码 iconphoto
        hiddenimports=[],
        hookspath=[],
        runtime_hooks=[],
        excludes=[],
        noarchive=False,
    )
    pyz = PYZ(a.pure)
    return EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name=f'{name}-{WM_BUILD_TAG}',
        icon='assets/icon.ico',   # EXE 资源嵌入主程序 icon
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,           # GUI 工具, 不带黑框
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )


build_exe('src/rename_tool.py')
