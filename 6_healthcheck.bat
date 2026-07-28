@echo off
chcp 949 >nul
REM 건강 점검(수집기 멈춤/카톡 로그아웃 감지). 스케줄러가 주기적으로 호출. 로그=healthcheck.log
cd /d "%~dp0"
set PY=py -3
%PY% --version >nul 2>&1
if errorlevel 1 set PY=python
%PY% healthcheck.py >> healthcheck.log 2>&1
