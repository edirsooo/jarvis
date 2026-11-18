@echo off
chcp 65001 >nul
title Jarvis
cd /d "%~dp0"
python jarvis.py --janela
pause
