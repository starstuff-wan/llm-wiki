@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [1/2] 编译 content/讲解.md ...
python build.py
if errorlevel 1 (
  echo.
  echo 构建失败。检查上面报错，或确认 python --version 能打印 3.12.x
  pause
  exit /b 1
)
echo.
echo [2/2] 启动本地服务器 http://127.0.0.1:8765
echo 关掉这个窗口就停止服务。
start "" http://127.0.0.1:8765
python -m http.server 8765 --directory docs
