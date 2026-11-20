@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3 -X utf8 "脚本\启动维护台.py"
pause
