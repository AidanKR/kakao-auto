@echo off
chcp 949 >nul
REM 클립보드로 대화 추출이 되는지 테스트. 결과는 probe.txt 에 저장.
cd /d "%~dp0"
echo 테스트할 대화방을 "더블클릭"해서 별도 창으로 띄운 뒤 계속하세요.
echo (테스트 중 그 방에서 Ctrl+A, Ctrl+C 가 자동 입력됩니다)
pause
python probe.py > probe.txt 2>&1
echo.
echo probe.txt 생성 완료. 이 파일 내용을 채팅에 붙여넣어 주세요.
notepad probe.txt
pause
