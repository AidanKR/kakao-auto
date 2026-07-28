@echo off
chcp 949 >nul
REM 일일 브리핑/응답대기 목록 생성. 스케줄러가 매일 아침 호출. 로그=briefing.log
cd /d "%~dp0"
set PY=py -3
%PY% --version >nul 2>&1
if errorlevel 1 set PY=python
%PY% briefing.py >> briefing.log 2>&1
