# HANDOFF — 다음 Claude Code(윈도우 PC)에게

이 문서는 이 프로젝트를 **다른 PC의 Claude Code**가 이어받아 마무리하도록 쓴 인수인계서다.
(맥에서 초안 작성 → USB로 윈도우 수집 PC 이전 → 그 PC에서 실측/튜닝하는 흐름)

## 무엇을 만드는가
카카오톡 PC(윈도우)의 **업무 전용 계정** 대화를, 창을 UI Automation(UIA)으로 읽어
- `kakao.db`(SQLite)에 **중복 없이 누적**하고
- 하루 2번(11:50, 23:50) **공유폴더에 날짜·방별 TXT로 정리**한다.

## 법적/정책 위치 (사용자와 합의된 전제)
- 본인 PC에서 본인 계정이 받은 메시지를 **읽기만** 함 → 형사상 불법 아님.
- 단 **카카오 이용약관 위반**이며 카톡 업데이트로 깨질 수 있음. 사용자는 이를 감수하기로 함.
- **업무 전용 계정**이라 타인 사생활 이슈는 낮음.

## 아키텍처
| 파일 | 역할 |
|---|---|
| `collector.py` | 상시 수집. **cycle 모드**(기본)=메인창 채팅목록을 하나씩 자동 선택하며 전부 순회. windows 모드=띄운 창만. |
| `consolidate.py` | DB → 공유폴더 정리(날짜/방별 TXT + `_전체.txt` + DB사본). 하루 2번 스케줄. |
| `discover.py` | 카톡 창 UIA 트리 덤프(버전별 튜닝용). Rect(좌표)로 좌=채팅목록 / 우=메시지 구분. |
| `db.py` | SQLite 스키마 + sha256 기반 중복제거. |
| `summarize.py` | (옵션) GPT 요약. |
| `1~5_*.bat`, `run_consolidate.bat` | 더블클릭 실행기 / 스케줄 등록. |

## 핵심 설계 결정
- 사용자 대화방이 **약 90개** → 창을 다 띄우는 건 불가 → **cycle(자동 순회)** 을 기본으로 함.
- cycle 은 방을 '선택'하므로 **읽음 처리** 부작용이 있음(업무 모니터링이라 허용).
- 방 선택은 마우스 클릭 대신 **UIA SelectionItem.Select()** 우선(실패 시 Click). **메시지 전송은 절대 안 함**(읽기 전용).
- 좌/우 패널 구분은 **BoundingRectangle.left** 로: 채팅목록=가장 왼쪽 리스트, 읽기영역=그 외 오른쪽 리스트.

## ⚠ 아직 안 끝난 일 (여기서 해야 함)
카톡 버전마다 UIA 구조가 달라서 **실측 튜닝이 남아있다.**
1. `2_discover.bat` 실행 → `tree.txt` 생성 (메인창 + 아무 방 1개 클릭한 상태).
2. `tree.txt` 에서 확인/반영:
   - **채팅목록 리스트**의 `Class`(→ config `chat_list_class`) 와 위치(가장 왼쪽인지).
   - **메시지 리스트**(오른쪽)의 `Class`, 그리고 각 메시지 ListItem 의 **Name 포맷**.
   - 메시지 Name 이 `보낸사람\n시간\n내용` 형태가 아니면 `collector.py`의 `parse_item()` 을 실제 포맷에 맞게 수정.
   - 채팅목록 아이템 Name 에서 방 이름 뽑는 `room_name_from_item()` 도 실제 포맷 확인.
3. `python collector.py` 로 몇 분 돌려 `kakao.db` 에 정상 적재되는지 확인.
4. `python consolidate.py` 로 공유폴더 정리 확인 → `5_autostart.bat` 로 자동화.

## 알려진 한계
- 폴링 사이 **화면 밖으로 스크롤된 과거 메시지**는 놓칠 수 있음(과거 이력 백필은 미구현 — 필요하면 스크롤업 백필 추가).
- 카톡 시간표기 없는 메시지는 동일내용 반복이 1건으로 합쳐질 수 있음(`db.make_hash` 한계).
- 이미지/파일/이모티콘은 텍스트로만 표기되거나 누락될 수 있음.

## 무인 자동 지속 (재부팅/카톡 재시작)
- `watchdog.bat`: 수집기가 죽으면 5초 뒤 재시작(무한 루프), `py -3`→`python` 자동선택, 로그=`collector.log`.
- `collector.py` 메인 루프는 **모든 예외를 잡고 계속** 돎 → 카톡 재시작 순간의 UIA 오류에도 안 죽음.
- `5_autostart.bat`: ONLOGON 으로 watchdog 등록 + 정리 11:50/23:50 + powercfg 절전끄기 + 화면보호기 끄기.
- **사람이 1회 수동**: 윈도우 자동로그인(netplwiz), 카톡 자동실행·자동로그인, 화면잠금 끄기.
  (cycle 은 GUI 조작이라 세션0 서비스로는 불가 — 반드시 잠기지 않은 로그인 세션에서 돌아야 함.)

## 환경 / 대상 PC 특성
- 대상: **아주 느린 새 Windows 10 64bit**(Python 미설치 상태에서 시작).
- `1_install.bat` 이 Python 유무 감지 → 없으면 python.org 다운로드 페이지를 열어줌(설치 시 "Add to PATH" 필수).
- 느린 PC라 `config.json` 기본 `dwell_ms=700`(방 선택 후 로딩 대기). 메시지 놓치면 900~1200 으로.
- `pip install -r requirements.txt`(uiautomation, pywin32, openai).
- 원저작 세션: macOS의 Claude Code에서 초안 작성(맥에선 uiautomation 실행 불가, 문법만 검증함).
