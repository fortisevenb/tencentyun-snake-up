@echo off
cd /d "%~dp0"
title 腾讯云秒杀 - 1. 获取登录 Cookie

echo =======================================================
echo        腾讯云秒杀助手 - 获取登录凭据 (Cookie ^& Token)
echo =======================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境 .venv！
    pause
    exit /b 1
)

echo 正在启动浏览器，请在弹出的窗口中扫码登录...
.venv\Scripts\python.exe get_cookies.py

echo.
echo 执行完毕，按任意键退出...
pause >nul
