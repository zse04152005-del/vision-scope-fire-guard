#!/bin/bash
# VisionScope 一键启动脚本 (macOS / Linux)
# 双击此文件或在终端运行: bash run.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================="
echo "  VisionScope 校园火警监控系统"
echo "=============================="
echo ""

# 检查 Python
if ! command -v python3 &>/dev/null; then
    echo "[错误] 未找到 Python3，请先安装 Python 3.9+"
    echo "  下载地址: https://www.python.org/downloads/"
    read -p "按回车键退出..."
    exit 1
fi

PYTHON=python3

# 检查依赖
echo "[1/3] 检查依赖..."
$PYTHON -c "import ultralytics, cv2, PyQt6" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "  首次运行，正在安装依赖（可能需要几分钟）..."
    $PYTHON -m pip install -r requirements.txt --quiet
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败，请手动运行: pip install -r requirements.txt"
        read -p "按回车键退出..."
        exit 1
    fi
    echo "  依赖安装完成!"
fi

# 检查模型
echo "[2/3] 检查模型文件..."
if [ ! -f "best.pt" ]; then
    echo "[警告] 未找到模型文件 best.pt，请将训练好的模型放到此目录"
    read -p "按回车键退出..."
    exit 1
fi

# 启动
echo "[3/3] 启动系统..."
echo ""
$PYTHON main.py "$@"
