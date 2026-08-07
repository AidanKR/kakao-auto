@echo off
chcp 949 >nul
REM 통합 검색 페이지 생성 후 열기. 전 대화를 한 칸에서 검색. 오프라인/로컬.
cd /d "%~dp0"
set PY=py -3
%PY% --version >nul 2>&1
if errorlevel 1 set PY=python
%PY% search.py --out "%~dp0검색.html"
if exist "%~dp0검색.html" start "" "%~dp0검색.html"
pause
