# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 — 生成独立可执行程序

使用方法:
  1. 安装 PyInstaller:  pip install pyinstaller
  2. 打包:             pyinstaller build_app.spec
  3. 输出在 dist/VisionScope/ 目录

注意:
  - best.pt 模型文件会被打包进去（约 6~50MB）
  - 首次打包可能需要较长时间
  - macOS 用户打包后在 dist/VisionScope/ 下双击 VisionScope 即可运行
  - Windows 用户打包后在 dist/VisionScope/ 下双击 VisionScope.exe 即可运行
"""

import os
import sys

block_cipher = None

# 项目根目录
BASE = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(BASE, 'main.py')],
    pathex=[BASE],
    binaries=[],
    datas=[
        # 模型文件
        (os.path.join(BASE, 'best.pt'), '.'),
        # 配置文件
        (os.path.join(BASE, 'config.json'), '.'),
    ],
    hiddenimports=[
        'ultralytics',
        'cv2',
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'psutil',
        'numpy',
        'torch',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VisionScope',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 无控制台窗口
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VisionScope',
)
