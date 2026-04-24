@echo off
chcp 65001 >nul 2>&1
title VisionScope 校园火警监控系统
cd /d "%~dp0"

echo ==============================
echo   VisionScope 校园火警监控系统
echo ==============================
echo.

:: 检查 Python
where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.9+
    echo   下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

set PYTHON=python

:: 检查依赖
echo [1/3] 检查依赖...
%PYTHON% -c "import ultralytics, cv2, PyQt6" 2>nul
if errorlevel 1 (
    echo   首次运行，正在安装依赖（可能需要几分钟）...
    %PYTHON% -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请手动运行: pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo   依赖安装完成!
)

:: 检查模型
echo [2/3] 检查模型文件...
if not exist "best.pt" (
    echo [警告] 未找到模型文件 best.pt，请将训练好的模型放到此目录
    pause
    exit /b 1
)

:: 启动
echo [3/3] 启动系统...
echo.
%PYTHON% main.py %*
if errorlevel 1 pause
