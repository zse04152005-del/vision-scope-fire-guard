@echo off
chcp 65001 >nul 2>&1
title VisionScope 校园火警监控系统
cd /d "%~dp0"

echo.
echo   ==================================
echo     VisionScope 校园火警监控系统
echo   ==================================
echo.

:: ---------- 检查 Python ----------
set PYTHON=
where python >nul 2>&1
if not errorlevel 1 (
    set PYTHON=python
    goto :found_python
)
where python3 >nul 2>&1
if not errorlevel 1 (
    set PYTHON=python3
    goto :found_python
)

echo   [错误] 未找到 Python
echo.
echo   请先安装 Python 3.9 或更高版本:
echo     下载地址: https://www.python.org/downloads/
echo.
echo   !! 安装时务必勾选 "Add Python to PATH" !!
echo.
pause
exit /b 1

:found_python
:: 显示版本
for /f "tokens=*" %%i in ('%PYTHON% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PY_VER=%%i
echo   Python 版本: %PY_VER%
echo.

:: ---------- 检查并安装依赖 ----------
echo   [1/3] 检查依赖包...
%PYTHON% -c "import ultralytics, cv2, PyQt6" 2>nul
if errorlevel 1 (
    echo.
    echo   首次运行，正在安装依赖包...
    echo   （需要联网，可能需要 2~5 分钟，请耐心等待）
    echo.
    %PYTHON% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo   [错误] 依赖安装失败
        echo   请尝试手动运行: %PYTHON% -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo.
    echo   依赖安装完成!
    echo.
)

:: ---------- 检查模型文件 ----------
echo   [2/3] 检查模型文件...
if not exist "best.pt" (
    echo.
    echo   [错误] 未找到模型文件 best.pt
    echo.
    echo   请将训练好的 YOLOv8 模型文件 (best.pt) 放到以下目录:
    echo     %cd%
    echo.
    pause
    exit /b 1
)
echo   模型文件: best.pt  OK

:: ---------- 启动程序 ----------
echo   [3/3] 启动系统...
echo.
echo   ==================================
echo     系统启动中，请稍候...
echo   ==================================
echo.
%PYTHON% main.py %*

:: 如果异常退出保持窗口
if errorlevel 1 (
    echo.
    echo   程序异常退出，请检查上方错误信息
    pause
)
