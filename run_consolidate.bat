@echo off
chcp 949 >nul
REM 스케줄러가 부르는 조용한 정리 실행기(멈춤 없음). 결과는 consolidate.log 에 기록.
cd /d "%~dp0"
python consolidate.py >> consolidate.log 2>&1
