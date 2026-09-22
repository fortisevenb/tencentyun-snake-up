@echo off
cd /d "%~dp0"
title 推送项目到 GitHub

echo =======================================================
echo    准备将代码推送到你的 GitHub 仓库:
echo    https://github.com/fortisevenb/tencentyun-snake-up
echo =======================================================
echo.

echo 正在尝试推送代码...
git -c http.sslVerify=false push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo =======================================================
    echo [成功] 代码已成功推送到你的 GitHub 仓库！
    echo 仓库链接: https://github.com/fortisevenb/tencentyun-snake-up
    echo =======================================================
) else (
    echo.
    echo [提示] 如果弹出 GitHub 授权窗口，请在浏览器中点击确认授权。
)

echo.
pause
