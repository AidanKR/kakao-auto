@echo off
chcp 949 >nul
REM 금액·약속·계좌 자동 추출 -> CSV(엑셀). 카톡 주문/정산 손입력 줄이기. 로컬.
cd /d "%~dp0"
set PY=py -3
%PY% --version >nul 2>&1
if errorlevel 1 set PY=python
%PY% extract.py --out "%~dp0추출_금액약속.csv"
if exist "%~dp0추출_금액약속.csv" start "" "%~dp0추출_금액약속.csv"
pause
