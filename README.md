# kakao-auto — 카카오톡 업무대화 자동 수집·정리 (Windows)

카카오톡 **대화방을 전부 자동 순회**하며 `Ctrl+S`(대화 내보내기)로 전체 기록을 뽑아
**SQLite 누적**하고, 하루 2번 **공유폴더에 날짜·방별 TXT로 정리**하며,
**무인 운영 상태를 스스로 감시·알림**하는 도구.

---

# ⚠️ USE AT YOUR OWN RISK — 반드시 먼저 읽으세요

> ### 이 도구를 실행하는 순간, 아래 모든 책임과 위험을 **전적으로 본인이** 진다는 데 동의하는 것입니다.
> ### 동의하지 않으면 **사용하지 마세요.** (전문: [LICENSE](LICENSE))

**이 프로젝트는 카카오(Kakao)와 아무 관련이 없는 비공식 개인 아카이빙 도구입니다.**

| | |
|---|---|
| 🚫 **약관 위반** | 카톡 클라이언트 자동화·스크래핑은 **카카오 이용약관 위반**입니다. **계정이 정지·삭제될 수 있습니다.** 그 위험은 온전히 본인 몫입니다. |
| ⚖️ **개인정보 책임=본인** | 수집물엔 **타인(고객·거래처)의 개인정보**가 담깁니다. **개인정보보호법(PIPA) 등 준수 책임은 100% 사용자**에게 있습니다(안전조치·목적제한·과도공유 금지·파기요청 대응). |
| 🙅 **금지 용도** | 타인 감시·무단 접근·본인이 당사자가 아닌 대화 감청·기타 불법 목적 **금지.** 본인 소유 계정 / 본인이 참여한 대화 / 적법한 목적에만. |
| 📵 **무보증·무책임** | **AS-IS.** 카톡 업데이트로 언제든 깨질 수 있고, 저자는 사용·오용으로 인한 **어떤 손해·계정조치·규제·법적 책임도 지지 않습니다.** |
| ✅ **전제 조건** | 본인 소유 **업무 전용 계정** · **읽기 전용**(전송·자동발송 안 함) · **비공개 저장**(백업 암호화 권장). |

> **ENGLISH — USE AT YOUR OWN RISK.** Independent, unofficial **personal archiving** tool, **NOT affiliated with Kakao**. Automating the KakaoTalk client **violates Kakao's Terms of Service** and may get your account suspended or terminated. It is **not hacking or wiretapping** — it reads your own messages, on your own PC, in conversations you are a party to. The collected data contains **other people's personal information**; **YOU are the data controller** and are solely responsible for lawful, secure handling under applicable privacy law (e.g., Korea's PIPA). **Own account only. Read-only. Private storage. No warranty. No liability. By using this software you accept full responsibility.** See [LICENSE](LICENSE).

## 신뢰성/모니터링 (무인 운영 안전장치)
- **health.json** — 매 바퀴 상태 기록(수집 방수·커버리지·신규건수·오류). 공유폴더에도 복사.
- **자동 알림**(`alerts.py`) — 커버리지 저하/카톡 미실행/오류 시 **공유폴더 `ALERT.txt` + 웹훅**(선택)으로 통지.
- **healthcheck.py** — 스케줄러가 30분마다 실행. 수집기가 **완전히 멈춘 경우**(health 갱신 정체)를 감지해 긴급 알림. `5_autostart.bat`이 자동 등록.
- 설정: `config.json`의 `alert_webhook_url`·`coverage_min_ratio`·`health_stale_minutes`.

## 데이터 품질 (②)
- **시간 정규화** — `오전/오후 H:MM` → 정렬가능한 ISO(`2026-07-07T15:01:00`). 정확한 정렬·기간조회 가능.
- **실제 메시지 날짜 기준 정리** — 언제 수집했든 **메시지가 실제로 온 날짜**(`sent_date`)의 파일로 들어감.
- **순번 중복구분** — 같은 사람이 같은 분에 똑같은 내용을 보내도(예: "네" "네") 순번(`seq`)으로 구분해 유실 없음.
- **증분 정리** — 새 메시지가 있는 날짜만 다시 씀(구글드라이브 동기화 최소화). 초기 백필은 `python consolidate.py --all`.
- **자동 마이그레이션** — 구버전 DB는 `collector` 첫 실행 시 자동 변환(유실 없음).

## AI 가치 — "내가 답할 것" + 일일 브리핑 (③)
`briefing.py` (매일 08:30 자동, `7_briefing.bat`).
- **응답 대기 감지(규칙 기반, AI 키 없어도 작동)** — 방마다 **마지막 메시지가 내가 아닌 사람**이면 = 응답 대기. 질문 여부·미답 시간·연속 건수로 우선순위 정렬 → `_daily/응답대기_날짜.txt`.
  - 내(계정 주인) 이름은 `config.json`의 `my_names`로 지정(비우면 자동 추정).
- **AI 브리핑(키 있으면)** — `ai_provider`(openai/anthropic)+`ai_api_key` 설정 시: **① 상황 요약 ② 먼저 답할 것 ③ 응답 초안**을 `_daily/브리핑_날짜.md`로 생성.
- ⚠️ **자동 발송 없음** — 초안만 만들고, 보내는 건 사람이 확인 후. (카톡은 전송 API도 없고, 수집기는 읽기 전용 유지)

## 엑셀(xlsx) 내보내기
`export_excel.py` / `12_excel.bat` — **방목록**·**응답대기**·**메시지** 3시트 엑셀로. 한글 헤더·필터·헤더 고정. 정산 근거·문의 목록을 엑셀로 바로. (`openpyxl` 필요, `1_install.bat` 설치)

## 통합 검색
`search.py` / `11_search.bat` — 모든 대화를 한 칸에서 검색(키워드 여러 개=모두 포함, 방·날짜 필터, 하이라이트, 최신순). 카톡 기본 검색(방 하나씩)과 달리 전 대화를 한 번에. 자체완결 HTML, 오프라인.

## 대시보드 (매일 여는 화면)
`dashboard.py` / `10_dashboard.bat` — 열자마자 오늘 상황이 한 장에. **지표 카드**(오늘 메시지·응답 대기·활동한 방·조용해진 방) + **먼저 답할 것**(질문·미답시간 우선) + **최근 14일 활동 히트맵**(진할수록 활발) + **조용해진 방**(N일 이상 소식 없음 → 놓친 관계 잡기). 서버에서 정적 HTML로 그려 넣어 **JS·외부 라이브러리 0**, 오프라인 동작. 설정: `quiet_days`·`dash_heatmap_days`·`dash_heatmap_rooms`.

## 2D 관계망 시각화
`graph_export.py` / `9_viz.bat` — DB에서 **방↔사람 + 방↔방(공통 참여자) 관계망**을 뽑아 **2D 인터랙티브 HTML** 생성(**노드 클릭=우측 패널: 실제 대화 + 참여자 목록** · **기간(날짜) 필터** · 드래그 이동 · 휠 확대 · 팬 · 이름 검색). **완전 자체완결**(외부 라이브러리·CDN 없음) → 인터넷 없이 더블클릭이면 열림. LLM·외부전송 0(전부 로컬). 활동 많은 방/사람이 크게, 소통 허브가 한눈에.
  - **방↔방 연결**(같은 사람이 겹치는 방, 허브 노이즈 자동 제외) · **색: 타입/최근활동** 전환 · **CSV 내보내기**(노드/연결).

## 보안 — 백업 + 암호화 (④)
`backup.py` (매일 02:00 자동, `8_backup.bat`).
- **회전 백업** — SQLite 온라인 백업(수집 중에도 안전) → gzip → `backups/`에 최근 N개 보관(`backup_keep`). 공유폴더(클라우드)에도 복사.
- **선택적 암호화** — `config.json`의 `backup_passphrase` 설정 시 백업을 **AES(Fernet)로 암호화** → 구글드라이브 유출돼도 안전. (`cryptography` 필요, `1_install.bat`이 설치)
  - ⚠️ 패스프레이즈 잊으면 복구 불가 — 안전한 곳에 따로 보관!
  - 암호화 켜면 `copy_db: false` 권장(공유폴더에 평문 DB 안 두기).
- **복구** — `python restore.py backups/kakao_...enc --pass "..."` → `kakao_restored.db` 로 풀림(라이브 DB 덮어쓰지 않음, 확인 후 교체).

## 요구사항
- **Windows** / Python 3.9+
- 카카오톡 로그인 + **메인 창을 크게 열어 두기**
- 방이 많으면(수십~수백 개) **cycle 모드**(기본): 프로그램이 채팅목록을 하나씩 자동 선택하며 전부 순회
  - ⚠ 방을 자동 선택하므로 해당 방이 **"읽음" 처리**됨(업무 모니터링 계정 전제)
  - ⚠ 순회 중엔 이 PC에서 카톡을 사람이 동시에 쓰기 어려움(전용 PC 권장)
- 방이 소수면 `mode: "windows"` 로 두고 방을 창으로 띄워 읽기 전용 수집도 가능

## 실행 순서 (전부 더블클릭)
| 순서 | 파일 | 하는 일 |
|---|---|---|
| 0 | (Python 없으면) `1_install.bat` 이 자동으로 다운로드 페이지를 엶 | 설치 시 **"Add python.exe to PATH" 체크** 필수 |
| 1 | `1_install.bat` | 파이썬 확인 + 라이브러리 설치(최초 1회, 인터넷 필요) |
| 2 | `2_discover.bat` | 카톡 창 구조를 `tree.txt`로 덤프(튜닝용, 1회) |
| — | `config.json` | `config.example.json` 복사 후 `mode`/`share_dir` 설정 |
| 3 | `3_collect.bat` | 수집 한 번 테스트(수동) |
| 4 | `4_consolidate.bat` | 정리를 지금 즉시 테스트 |
| 5 | `5_autostart.bat` | **무인 자동화 등록**(재부팅 시 수집기 자동시작 + 하루 2번 정리 + 절전끄기) |

## 무인(재부팅·카톡 재시작 자동 지속) 세팅
`5_autostart.bat` 이 등록하는 것:
- **수집기 자동시작**: 로그인 시 `watchdog.bat` 실행 → 수집기가 죽으면 5초 뒤 자동 재시작(`collector.log` 기록)
- **정리 자동**: 매일 11:50 / 23:50
- **절전/화면보호기 끄기**: 항상 켜둔 PC용

수집기 루프는 **카톡이 꺼졌다 켜져도** 창을 다시 찾을 때까지 기다렸다 계속 수집(예외에도 안 죽음).

### 사람이 딱 3가지만 1회 설정 (이게 돼야 재부팅 후 무인 지속)
1. **윈도우 자동 로그인**: `Win+R` → `netplwiz` → 사용자 선택 → "사용자 이름과 암호를 입력해야…" 체크 해제 → 암호 입력
2. **카카오톡**: 설정 → "PC 켤 때 자동 실행" + "자동 로그인" 켜기
3. **화면 잠금 끄기**(잠기면 cycle 자동수집 불가): 설정 → 계정 → 로그인 옵션 → "다시 로그인 필요" = 안 함

> 이유: cycle 모드는 GUI를 조작(방 선택)하므로 **로그인된 잠기지 않은 데스크톱 세션**이 떠 있어야 함.
> 그래서 서비스(세션0)가 아니라 로그인 세션에서 도는 구조다.

## 설정 (config.json)
```jsonc
{
  "rooms": [],                    // [] = 열린 모든 대화창 자동 수집. 특정 방만: ["영업1팀","CS"]
  "poll_seconds": 3,             // 몇 초마다 읽을지
  "share_dir": "C:\\kakao_share", // 정리본 저장 공유폴더(다른 PC에서 열람)
  "copy_db": true                // DB 사본도 공유폴더에 복사
}
```
- **다른 PC에서 불러오기:** `share_dir` 를 네트워크 공유폴더(예: `\\서버\공유\kakao`)로 지정하면,
  정리된 `날짜/방이름.txt` 와 `_전체.txt` 를 다른 PC에서 그대로 열 수 있습니다.

## 새 방 자동 감지
cycle 모드는 매 순회마다 채팅목록 전체를 다시 읽으므로 **새로 생긴 방도 다음 바퀴에 자동 수집**됩니다.
- 처음 보는 방이면 콘솔에 `[새 방 감지]` 출력 + `new_rooms.log` 에 `시각\t방이름` 기록
- DB `rooms` 테이블에 방 레지스트리(최초발견/마지막/누적건수) 유지
- 정리 시 공유폴더 루트에 `rooms_seen.txt`(전체 방 목록) 최신본 출력 → 다른 PC에서 확인
> (구조 스냅샷 `tree.txt` 는 방 목록이 아니라 UIA 튜닝용 1회 파일이라 여기엔 방을 넣지 않습니다.)

## 나오는 결과물
```
C:\kakao_share\
  2026-07-07\
    _전체.txt          ← 그날 모든 방 합본
    영업1팀.txt
    CS문의.txt
  kakao.db             ← DB 사본(다른 PC에서 조회용)
```

## GPT 요약 (옵션)
```bat
set OPENAI_API_KEY=sk-...
python summarize.py --room "영업1팀" --date 2026-07-07
python summarize.py --room "영업1팀" --days 7
python summarize.py --room "영업1팀" --date 2026-07-07 --raw
```

## 파일
| 파일 | 역할 |
|---|---|
| `collector.py` | 열린 대화창 전부 실시간 수집 → SQLite |
| `consolidate.py` | 날짜·방별 정리 → 공유폴더(하루 2번 스케줄) |
| `discover.py` | 카톡 창 구조 덤프(튜닝용) |
| `db.py` | SQLite + 중복제거 |
| `summarize.py` | GPT 요약(옵션) |

## 한계 / 주의
- 창을 **닫거나 최소화하면** 그 방은 못 읽음. 창은 떠 있어야 함.
- 폴링 사이에 **화면 밖으로 스크롤된 과거 메시지**는 놓칠 수 있음 → `poll_seconds` 를 너무 길게 두지 말 것.
- 카톡 업데이트 후 안 읽히면 `2_discover.bat` 다시 돌려 `list_class` 갱신.
- 정리 로그: `consolidate.log`.
