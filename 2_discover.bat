@echo off
chcp 949 >nul
REM 카톡 창 구조를 tree.txt 로 덤프 (수집기 튜닝용, 1회)
cd /d "%~dp0"
echo 카카오톡 로그인 후, 메인 창에서 아무 방이나 "한 번 클릭"해 오른쪽에 대화가 보이게 한 뒤 계속하세요.
pause
python discover.py > tree.txt 2>&1
echo.
echo tree.txt 생성 완료. 이 파일을 USB로 가져와서 붙여넣어 주세요.
pause
