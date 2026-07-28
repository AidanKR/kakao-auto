@echo off
chcp 949 >nul
title KakaoCollector (watchdog)
cd /d "%~dp0"

REM 파이썬 실행기 결정: py -3 우선, 없으면 python
set PY=py -3
%PY% --version >nul 2>&1
if errorlevel 1 set PY=python

echo [watchdog] 수집기를 감시하며 계속 살립니다. 이 창을 닫지 마세요.
echo [watchdog] 사용 파이썬: %PY%
echo.

:loop
echo [%date% %time%] 수집기 시작
%PY% collector.py >> collector.log 2>&1
echo [%date% %time%] 수집기 종료됨(코드 %errorlevel%). 5초 후 재시작...
timeout /t 5 /nobreak >nul
goto loop
