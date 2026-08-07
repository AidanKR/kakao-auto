@echo off
chcp 949 >nul
REM 엑셀(xlsx) 내보내기 - 방목록/응답대기/메시지. 실무용. 로컬 처리.
cd /d "%~dp0"
set PY=py -3
%PY% --version >nul 2>&1
if errorlevel 1 set PY=python
%PY% export_excel.py --out "%~dp0카카오톡.xlsx"
if exist "%~dp0카카오톡.xlsx" start "" "%~dp0카카오톡.xlsx"
pause
