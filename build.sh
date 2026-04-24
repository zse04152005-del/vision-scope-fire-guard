#!/bin/bash
# VisionScope 打包脚本 — 生成独立可执行程序
# 使用方法: bash build.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================="
echo "  VisionScope 打包工具"
echo "=============================="
echo ""

# 检查 PyInstaller
python3 -c "import PyInstaller" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "正在安装 PyInstaller..."
    python3 -m pip install pyinstaller --quiet
fi

echo "开始打包（可能需要几分钟）..."
echo ""

python3 -m PyInstaller build_app.spec --noconfirm

if [ $? -eq 0 ]; then
    echo ""
    echo "=============================="
    echo "  打包成功!"
    echo "  输出目录: dist/VisionScope/"
    echo "=============================="
else
    echo ""
    echo "[错误] 打包失败，请检查错误信息"
fi
