@echo off
chcp 949 >nul
REM DB 백업(회전+선택 암호화). 스케줄러가 매일 02:00 호출. 로그=backup.log
cd /d "%~dp0"
set PY=py -3
%PY% --version >nul 2>&1
if errorlevel 1 set PY=python
%PY% backup.py >> backup.log 2>&1
