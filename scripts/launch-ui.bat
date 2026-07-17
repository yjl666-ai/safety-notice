@echo off
chcp 65001 >nul
title 智安通 - Web UI 启动器

echo ============================================
echo   智安通 - Web UI 启动器
echo ============================================
echo.

REM 1. 启动 Flask 服务(后台,不弹 wsl 窗口)
wsl -d Ubuntu bash -c "cd '/mnt/d/新建文件夹/龙虾/safety-notice' && nohup ./venv/bin/python app.py > ui.log 2>&1 &" 2>nul

REM 2. 等 4 秒让 Flask 起来
echo 启动 Flask 服务中... 等待 4 秒
ping -n 5 127.0.0.1 >nul 2>&1

REM 3. 打开浏览器
echo 打开浏览器...
start "" "http://localhost:5000"

echo.
echo 浏览器已打开 http://localhost:5000
echo 服务跑在后台(WSL 里)。要停止服务,在 WSL 跑:
echo   pkill -f "python app.py"
echo.
echo 关闭此窗口不会停止服务。
echo.
pause
