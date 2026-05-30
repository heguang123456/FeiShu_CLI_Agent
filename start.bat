@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================
echo    飞书CLI笔记智能体 (NoteAgent) 启动器
echo ==========================================
echo.

:: 检查Python环境
echo [1/3] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请确保已安装Python 3.9+并添加到PATH
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [成功] Python版本: %PYTHON_VERSION%

:: 检查依赖包
echo.
echo [2/3] 检查依赖包...
python -c "import langchain" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖包...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖包安装失败
        pause
        exit /b 1
    )
)
echo [成功] 依赖包已就绪

:: 检查飞书CLI登录状态
echo.
echo [3/3] 检查飞书CLI登录状态...
lark-cli --version >nul 2>&1
if errorlevel 1 (
    echo [警告] 未找到lark-cli，请确保已安装飞书CLI
    echo 安装指南: https://github.com/larksuite/cli
    echo.
    echo 继续启动程序，但部分功能可能不可用...
) else (
    echo [成功] 飞书CLI已安装
    lark-cli auth status >nul 2>&1
    if errorlevel 1 (
        echo [提示] 飞书CLI未登录，正在尝试登录...
        lark-cli auth login
    ) else (
        echo [成功] 飞书CLI已登录
    )
)

echo.
echo ==========================================
echo    启动NoteAgent...
echo ==========================================
echo.

:: 启动主程序
python main.py

:: 保持控制台开启
echo.
echo 程序已退出，按任意键关闭窗口...
pause >nul