@echo off
cd /d "%~dp0"
title 腾讯云秒杀 - 2. 启动秒杀主程序

echo =======================================================
echo        腾讯云秒杀助手 - 启动秒杀抢购主程序
echo =======================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境 .venv！
    pause
    exit /b 1
)

if not exist "cookies.json" (
    echo [提示] 未检测到 cookies.json 文件！
    echo 请先双击运行 "1_获取登录Cookie.bat" 进行扫码登录。
    echo.
    pause
    exit /b 1
)

.venv\Scripts\python.exe snap_up_server.py

echo.
echo 执行完毕，按任意键退出...
pause >nul
