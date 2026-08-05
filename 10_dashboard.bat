@echo off
chcp 949 >nul
REM 대시보드 생성 후 브라우저로 열기. LLM/외부전송 없음(로컬 처리).
cd /d "%~dp0"
set PY=py -3
%PY% --version >nul 2>&1
if errorlevel 1 set PY=python
%PY% dashboard.py --out "%~dp0dashboard.html"
if exist "%~dp0dashboard.html" start "" "%~dp0dashboard.html"
pause
