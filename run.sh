#!/bin/bash
# VisionScope 一键启动脚本 (macOS / Linux)
# 使用方法: 在终端运行 bash run.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  =================================="
echo "    VisionScope 校园火警监控系统"
echo "  =================================="
echo ""

# ---------- 检查 Python ----------
PYTHON=""
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
fi

if [ -z "$PYTHON" ]; then
    echo "  [错误] 未找到 Python"
    echo ""
    echo "  请先安装 Python 3.9 或更高版本:"
    echo "    Mac:     brew install python3"
    echo "    或访问:  https://www.python.org/downloads/"
    echo ""
    read -p "  按回车键退出..."
    exit 1
fi

# 检查版本
PY_VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
echo "  Python 版本: $PY_VER"
echo ""

# ---------- 检查并安装依赖 ----------
echo "  [1/3] 检查依赖包..."
$PYTHON -c "import ultralytics, cv2, PyQt6" 2>/dev/null
if [ $? -ne 0 ]; then
    echo ""
    echo "  首次运行，正在安装依赖包..."
    echo "  （需要联网，可能需要 2~5 分钟，请耐心等待）"
    echo ""
    $PYTHON -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo ""
        echo "  [错误] 依赖安装失败"
        echo "  请尝试手动运行: $PYTHON -m pip install -r requirements.txt"
        echo ""
        read -p "  按回车键退出..."
        exit 1
    fi
    echo ""
    echo "  依赖安装完成!"
    echo ""
fi

# ---------- 检查模型文件 ----------
echo "  [2/3] 检查模型文件..."
if [ ! -f "best.pt" ]; then
    echo ""
    echo "  [错误] 未找到模型文件 best.pt"
    echo ""
    echo "  请将训练好的 YOLOv8 模型文件 (best.pt) 放到以下目录:"
    echo "    $SCRIPT_DIR/"
    echo ""
    read -p "  按回车键退出..."
    exit 1
fi
echo "  模型文件: best.pt  OK"

# ---------- 启动程序 ----------
echo "  [3/3] 启动系统..."
echo ""
echo "  =================================="
echo "    系统启动中，请稍候..."
echo "  =================================="
echo ""
$PYTHON main.py "$@"

# 如果程序异常退出，保持窗口
if [ $? -ne 0 ]; then
    echo ""
    echo "  程序异常退出，请检查上方错误信息"
    read -p "  按回车键退出..."
fi
