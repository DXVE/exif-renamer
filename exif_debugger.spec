# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec: 调试工具 exif_debugger.py
产物名: exif_debugger-<BUILD_TS>.exe (跟随原脚本名)
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
        datas=[],
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


build_exe('src/exif_debugger.py')
