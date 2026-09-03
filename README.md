# kakao-auto — KakaoTalk Windows Auto Chat Collector & Archiver

![platform](https://img.shields.io/badge/platform-Windows-0078D6)
![python](https://img.shields.io/badge/python-3.9%2B-3776AB)
![license](https://img.shields.io/github/license/AidanKR/kakao-auto)
![stars](https://img.shields.io/github/stars/AidanKR/kakao-auto?style=flat)
![last commit](https://img.shields.io/github/last-commit/AidanKR/kakao-auto)

**Archive every KakaoTalk chat room on a Windows PC — automatically, every night, into one CSV per room.**

Leave KakaoTalk open on the Chats tab and press Enter. It cycles through every room, exports the full history via the app's own `Ctrl+S`, stores it in **SQLite**, and writes **one CSV per room** plus the real photos. Schedule it once and it runs at 2 AM with nobody at the machine — no monitor required. **Read-only** (it never sends a message) and **fully offline**.

한국어 안내는 [아래](#한국어) 에 있습니다.

<sub>KakaoTalk scraper · KakaoTalk exporter · chat archiver · KakaoTalk backup · Windows chat automation · read-only messenger backup · 카카오톡 자동 수집 · 카카오톡 대화 백업 · 카카오톡 스크래퍼 · 카카오톡 대화 내보내기 · 카톡 백업</sub>

![Dashboard — who's waiting on you, activity heatmap, gone-quiet rooms](docs/dashboard.png)

---

# ⚠️ USE AT YOUR OWN RISK — read this first

> **Running this tool means you accept every risk below, entirely. If you don't accept them, don't use it.** Full terms: [LICENSE](LICENSE) · [NOTICE](NOTICE)

**This is an independent, unofficial personal archiving tool. It is NOT affiliated with Kakao Corp.**

| | |
|---|---|
| 🚫 **Terms of Service** | Automating or scraping the KakaoTalk client **violates KakaoTalk's Terms of Service**. Your account **may be restricted, suspended, or terminated**. That risk is entirely yours. |
| ⚖️ **You are the data controller** | The archive contains **other people's personal information**. Compliance with privacy law (Korea's **PIPA** and any equivalent) is **100% your responsibility**. |
| 🙅 **Forbidden uses** | No surveillance of others, no unauthorized access, no interception of conversations you are not a party to, nothing unlawful. |
| 📵 **No warranty, no liability** | **AS IS.** A KakaoTalk update can break it at any time. The author is not liable for any damage, account action, or legal claim. |
| ✅ **Not an exploit** | It breaks no encryption and bypasses no authentication. It drives the app's own export, on your own PC, in rooms you already belong to. That still does not make it compliant with Kakao's terms. |

---

## Install (Windows)

**No Python, no build step.**

1. Download **`KakaoAuto-Setup.exe`** from [**Releases**](https://github.com/AidanKR/kakao-auto/releases/latest).
2. Run it. Windows shows **"Windows protected your PC"** because the binary is unsigned → **More info → Run anyway**.
3. Launch **KakaoAuto** from the Start menu.

It installs to `%LOCALAPPDATA%\KakaoAuto`, and keeps `config.json`, `kakao.db`, and all output next to the executable.

> The installer is built on a Windows CI runner — see `.github/workflows/build-windows.yml`.

## Use it — one keypress

**Prerequisite: KakaoTalk must be running and on the Chats tab.** Nothing is collected otherwise.

Start KakaoAuto and press **Enter**. That runs the whole pipeline:

```
collect → consolidate (optional) → one CSV per room → photo backup
```

The numbered menu entries are there for individual tools when you want them.

## Run it every night, unattended

Press **`11`** once. A daily task is registered for **02:00** that runs the same full pipeline. No admin rights needed; it also disables sleep. Press **`12`** to remove it.

- Change the time: set `"nightly_time": "02:00"` in `config.json`, then press `11` again.
- Requirements at that hour: the PC is **on, logged in, and unlocked**, and **KakaoTalk is running on the Chats tab**.
- **No monitor required.** Room cycling is keyboard-driven, so it works headless — verified on a laptop with a dead screen and nothing plugged in. Closing the lid is fine if the lid action is set to "Do nothing".
- KakaoTalk is **left running**. Set `close_kakao_after: true` if you would rather it be closed.

## What you get

Everything lands under `share_dir` (default `C:/kakao_share`) — point it at a Google Drive folder to sync it off the machine.

```
C:\kakao_share\
  csv\
    Sales Team\
      Sales Team.csv          ← one folder per room, one CSV inside
    Customer Support\
      Customer Support.csv
    _rooms_index.csv          ← room list, message counts, first/last timestamps
  media\                     ← real photos only (emoticons and stickers excluded)
  kakao.db                    ← copy of the SQLite database
```

- **CSV columns**: `room, date, time, datetime, sender, message`
- **Encoding** `utf-8-sig` — opens cleanly in Excel, reads straight into `pandas.read_csv`
- Rewritten in full on every run, so the CSVs are always the complete current archive
- Want human-readable daily transcripts too? Set `nightly_txt: true` → `share_dir/txt/<date>/<room>.txt`

## The rest of the toolbox

| Menu | What it does |
|---|---|
| `3` | **Dashboard** — who is still waiting on your reply, 14-day activity heatmap, clients who went quiet |
| `4` | **Full-text search** across every conversation at once (offline, single HTML file) |
| `5` | **Relationship graph** — rooms ↔ people, 2D and interactive |
| `6` | **Excel export** — rooms, pending replies, messages (3 sheets) |
| `7` | **Extract amounts, appointments, bank accounts** — regex, no AI required |
| `8` | **Photo backup** — save media before KakaoTalk expires it (emoticons excluded) |
| `9` | **Database backup** — rotating, with optional AES encryption |
| `10` | **Daily briefing / pending replies** — rule-based; optional AI summary, including local **Ollama** so nothing leaves the machine |
| `14` | **Calibrate the Chats tab** — for when KakaoTalk starts on the profile tab |

![Full-text search across every chat](docs/search.png)

![2D relationship graph — rooms and people](docs/graph.png)

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| It reads your friends list, not chats | KakaoTalk started on the **Friends tab**. Run menu `14` once to calibrate where the Chats icon is. |
| `채팅목록을 못 찾음` (chat list not found) | KakaoTalk is closed or not logged in. Open it and switch to the Chats tab. |
| The CSV folder is empty | Collecting only fills the database. Press **Enter** (full run) to produce CSVs. |
| Cycling gets confused | Don't touch the mouse or keyboard while the batch runs — it is driving the GUI. |
| Only emoticons got backed up | Check `skip_emoticons: true` (the default), and raise `media_min_bytes` to drop small images. |

## Configuration

New options are **filled into your `config.json` automatically** when a new version starts (your existing values are preserved; the original is saved as `config.json.bak`). You rarely need to edit it by hand.

The ones worth knowing:

```jsonc
{
  "share_dir": "C:/kakao_share",   // where output goes (a Google Drive path works)
  "nightly_time": "02:00",         // unattended run time, local to this PC
  "nightly_txt": false,            // also write daily TXT transcripts
  "nightly_media": true,           // include photo backup
  "close_kakao_after": false,      // close KakaoTalk when the batch finishes
  "backup_passphrase": ""          // set it to AES-encrypt database backups
}
```

## Running from source

On Windows: `1_install.bat` (dependencies) → copy `config.example.json` to `config.json` → `python kakao.py`. To build the executable yourself, run `build_exe.bat`.

## Requirements

- **Windows** — it drives the KakaoTalk desktop client, so there is no macOS or Linux build
- KakaoTalk logged in, on the **Chats tab**
- A dedicated machine is recommended; the PC is hard to use while a cycle is running

## How it reads messages (technical note)

This build of KakaoTalk draws its chat list and messages itself (owner-drawn), so UI Automation returns **no text at all** — you cannot scrape it the usual way. Instead this tool automates the application's own **`Ctrl+S` chat export** and parses the result. The save dialog is a modal that freezes UIA, so that step is handled through win32 instead. The friends list and the chat list use the *same* control class, so they are told apart by control name (`ChatRoomListCtrl`) — otherwise the collector happily archives your contact list.

---

<a name="한국어"></a>

## 한국어

**카카오톡 PC의 모든 대화방을 자동으로 순회해 수집하고, 방마다 CSV 한 장으로 정리하는 윈도우 전용 도구.**

### 설치
[Releases](https://github.com/AidanKR/kakao-auto/releases/latest) 에서 **`KakaoAuto-Setup.exe`** 를 받아 실행하세요. 파이썬도 빌드도 필요 없습니다. "Windows가 PC를 보호했습니다" 창이 뜨면 **추가 정보 → 실행** (서명 인증서가 없는 오픈소스라 정상입니다).

### 쓰는 법
**카카오톡을 켜고 '채팅' 탭으로 두세요.** 그 상태에서 KakaoAuto를 실행하고 **Enter만 누르면** 수집 → 정리 → 방별 CSV → 사진 백업이 한 번에 이어집니다.

### 매일 자동
메뉴 **`11`** 을 한 번 누르면 매일 **새벽 02:00** 에 같은 작업이 자동으로 돕니다(해제는 `12`). 그 시각에 PC가 켜져 있고 로그인 상태이며 카카오톡이 채팅 탭이면 됩니다. **모니터는 없어도 됩니다** — 방 순회가 키보드 방식이라 화면이 꺼진 상태에서도 동작합니다(실기 검증). 노트북 덮개를 닫아도 되지만, 덮개 동작을 "아무 것도 안 함"으로 두세요.

### 나오는 것
`share_dir`(기본 `C:/kakao_share`) 아래에 **방마다 폴더 하나 + CSV 하나**(`csv/<방>/<방>.csv`), 방 목록(`_rooms_index.csv`), 실제 사진만 담긴 `media/`, DB 사본이 쌓입니다. CSV 컬럼은 `room, date, time, datetime, sender, message` 이고 `utf-8-sig` 라 엑셀에서 한글이 안 깨지고 `pandas` 로 바로 읽힙니다.

### 그 밖에
대시보드(누구에게 답을 안 했는지), 통합 검색, 관계망, 엑셀, 금액·약속 추출, 사진 백업, 암호화 백업, 일일 브리핑(로컬 Ollama 가능)이 메뉴에 있습니다. 잘 안 될 때는 위 [Troubleshooting](#troubleshooting) 표를 보세요. 특히 **프로필/친구 목록만 읽히면 메뉴 `14`** 로 채팅 탭 위치를 한 번 보정하면 됩니다.

### 주의
카카오톡 클라이언트 자동화는 **카카오 이용약관 위반**이며 계정이 정지·삭제될 수 있습니다. 수집물에는 타인의 개인정보가 담기므로 **개인정보보호법(PIPA) 준수 책임은 사용자 본인**에게 있습니다. 본인 소유 계정, 본인이 참여한 대화, 적법한 목적에만 사용하세요.

## License

**Apache License 2.0** — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

Commercial use, modification, and redistribution are permitted free of charge. In return, Apache 2.0 requires that you:

- keep the copyright, patent, trademark, and attribution notices,
- **reproduce the contents of the [NOTICE](NOTICE) file** in any redistribution or derivative work (Section 4(d)), which is how the original author is credited,
- state that you changed any files you modified, and
- include a copy of the License.

It also grants an explicit patent license to users, and terminates that patent grant for anyone who starts patent litigation over the work.

> Created and maintained by **AidanKR (Lee Donghyuk)** — https://github.com/AidanKR/kakao-auto

## Disclaimer & Acceptable Use

**kakao-auto is an independent, unofficial personal archiving tool. It is NOT affiliated with, endorsed by, sponsored by, or connected to Kakao Corp. or KakaoTalk.**

"Kakao" and "KakaoTalk" are trademarks of Kakao Corp. Neither this software nor its license grants any right, title, license, or interest in any intellectual property, trademark, service, product, or data of Kakao Corp. or any other third party.

### Terms of Service — read this before you install

Automating, scraping, or otherwise driving the KakaoTalk desktop client **violates KakaoTalk's Terms of Service.** Using this software may result in **restriction, suspension, or permanent termination of your KakaoTalk account**, and Kakao may take other measures at its discretion. **That risk is entirely yours.** If you are not willing to accept it, do not use this software.

Kakao may change its client or its terms at any time, which can break this tool or increase the risk of using it, without notice.

### Privacy and personal data — you are the data controller

Conversation archives created with this software contain **other people's personal information**: names, phone numbers, addresses, order details, photographs, and more.

**You — not the author — are the data controller.** You are solely responsible for determining whether and how your use complies with applicable privacy and data-protection law, including the **Personal Information Protection Act (PIPA)** of the Republic of Korea and any equivalent law in your jurisdiction. That includes having a lawful basis, limiting purpose and retention, applying security safeguards (the tool ships optional AES backup encryption for this reason), and honoring access and deletion requests from data subjects.

Use only on an account you own, only for conversations you are a party to, and only for lawful purposes. **Do not** use this software for surveillance of others, unauthorized access, interception of communications you are not a party to, employee monitoring without a lawful basis, or any other unlawful purpose.

If you deploy this inside a company, treat the archive as a regulated personal-data store: restrict access, document the purpose, and set a retention period.

### No warranty, no liability

This software is provided under the Apache License 2.0 on an **"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND**, either express or implied. See Sections 7 and 8 of the [LICENSE](LICENSE).

To the maximum extent permitted by law, the author shall not be liable for any damages, data loss, account restriction or termination, regulatory penalty, or legal claim arising from your use or misuse of this software.

**This document is not legal advice.** If you intend to use this in a business context, get your own legal review first.

### Not affiliated, not an exploit

This tool does not break encryption, bypass authentication, or access anything you cannot already see yourself. It drives the KakaoTalk client's own **export** feature on your own machine, in conversations you are already a member of. It is **read-only** — it never sends a message. That does not make it compliant with Kakao's terms; see above.
