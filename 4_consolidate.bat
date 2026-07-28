@echo off
chcp 949 >nul
REM 정리를 지금 즉시 한 번 돌려보는 수동 실행(테스트용).
cd /d "%~dp0"
python consolidate.py
pause
