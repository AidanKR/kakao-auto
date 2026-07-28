"""
카카오톡 PC 메시지 수집기 v6 (Windows 전용) — Ctrl+S 내보내기 + 신뢰성 모니터링

방을 열고 Ctrl+S(대화 내보내기)로 전체 기록을 txt로 뽑아 읽는다(클립보드/좌표는 대체 경로).
매 바퀴 상태를 health.json 에 기록하고, 커버리지 저하/카톡 미실행/오류를 알림(alerts.py)한다.
수집기가 완전히 죽은 경우는 healthcheck.py(스케줄러)가 별도로 감지해 긴급 알림한다.

모드(config.json "mode"):
  - "cycle"   : 메인창 채팅목록을 좌표로 더블클릭해 방을 하나씩 열고 읽고 닫으며 전부 순회 (90개 자동)
  - "windows" : 이미 '별도 창'으로 띄워둔 방들만 클립보드로 읽음 (테스트/소수)

공통: 파싱 -> SQLite(중복 자동 제거) -> 방 레지스트리(새 방 감지).
정리/공유폴더 저장은 consolidate.py(하루 2번 스케줄).

⚠ 방을 열면 '읽음' 처리됨(업무 모니터링 계정 전제).
⚠ cycle 은 마우스를 자동으로 움직여 방을 연다 — 도는 동안 그 PC를 만지지 마세요(전용 PC).
"""
import ctypes
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import db
import alerts
import health

# 콘솔/로그 인코딩 문제로 죽지 않게(이모지·특수문자 등은 ? 로 대체)
try:
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except Exception:
    pass

try:
    import uiautomation as auto
except ImportError:
    print("uiautomation 미설치.  1_install.bat 먼저 실행")
    sys.exit(1)

try:                       # 저장창(모달)은 UIA가 멈춰서 win32로 다룬다
    import win32gui
    import win32con
except Exception:
    win32gui = None
    win32con = None

HERE = Path(__file__).parent
ITEM = ("ListItemControl", "DataItemControl")

MSG_RE = re.compile(r"^\[(.+?)\] \[(오전|오후) (\d{1,2}):(\d{2})\] (.*)$")
DATE_RE = re.compile(r"^(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일")

# ── 마우스(좌표) 제어 ────────────────────────────────────
try:
    _U32 = ctypes.windll.user32
except Exception:
    _U32 = None
_LDOWN, _LUP, _WHEEL = 0x0002, 0x0004, 0x0800


def _cursor(x, y):
    _U32.SetCursorPos(int(x), int(y))


def pixel_double_click(x, y):
    _cursor(x, y)
    time.sleep(0.05)
    for _ in range(2):
        _U32.mouse_event(_LDOWN, 0, 0, 0, 0)
        _U32.mouse_event(_LUP, 0, 0, 0, 0)
        time.sleep(0.03)


def pixel_wheel_down(x, y, notches):
    _cursor(x, y)
    time.sleep(0.05)
    _U32.mouse_event(_WHEEL, 0, 0, -120 * int(notches), 0)


# ── 설정 ─────────────────────────────────────────────────
def _read_smart(p):
    data = p.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def load_config():
    p = HERE / "config.json"
    if not p.exists():
        print("config.json 이 없습니다. config.example.json 을 복사해서 만드세요.")
        sys.exit(1)
    raw = _read_smart(p)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:                       # 흔한 실수: 경로 역슬래시 -> 슬래시로 고쳐 재시도
            return json.loads(raw.replace("\\", "/"))
        except json.JSONDecodeError as e:
            print(f"config.json 형식 오류: {e}")
            print('경로는 역슬래시 대신 / 를 쓰세요. 예: "C:/kakao_share"')
            sys.exit(1)


# ── UIA 헬퍼 ─────────────────────────────────────────────
def find_class(ctrl, classname, depth=0):
    if depth > 16:
        return None
    try:
        for c in ctrl.GetChildren():
            if (c.ClassName or "") == classname:
                return c
            r = find_class(c, classname, depth + 1)
            if r:
                return r
    except Exception:
        pass
    return None


def get_main_window():
    for w in auto.GetRootControl().GetChildren():
        if (w.ClassName or "") == "EVA_Window_Dblclk" and (w.Name or "") == "카카오톡":
            return w
    return None


def chat_windows_by_handle():
    hs = {}
    for w in auto.GetRootControl().GetChildren():
        if (w.ClassName or "") == "EVA_Window_Dblclk" and (w.Name or "").strip() and (w.Name or "") != "카카오톡":
            try:
                hs[w.NativeWindowHandle] = w
            except Exception:
                pass
    return hs


def close_window(win):
    try:
        win.GetWindowPattern().Close()
        return True
    except Exception:
        try:
            win.SetActive(); time.sleep(0.1); auto.SendKeys("{Esc}")
            return True
        except Exception:
            return False


def wait_closed(handle, timeout=2.0):
    for _ in range(int(timeout / 0.15) + 1):
        if handle not in chat_windows_by_handle():
            return True
        time.sleep(0.15)
    return False


# ── 클립보드 읽기 + 파서 ────────────────────────────────
def clip_read(win, dwell):
    try:
        win.SetActive()
    except Exception:
        pass
    time.sleep(dwell)
    msg = find_class(win, "EVA_VH_ListControl_Dblclk")
    if msg is None:
        return None
    try:
        msg.Click(simulateMove=False)
        time.sleep(0.2)
        auto.SetClipboardText("")
        time.sleep(0.1)
        auto.SendKeys("{Ctrl}(a)")
        time.sleep(0.2)
        auto.SendKeys("{Ctrl}(c)")
        time.sleep(0.3)
        return auto.GetClipboardText() or ""
    except Exception as e:
        print(f"  클립보드 읽기 오류: {e}")
        return None


def find_by_type(ctrl, typename, depth=0):
    if depth > 12:
        return None
    try:
        for c in ctrl.GetChildren():
            if c.ControlTypeName == typename:
                return c
            r = find_by_type(c, typename, depth + 1)
            if r:
                return r
    except Exception:
        pass
    return None


def find_save_dialog_hwnd(timeout=12):
    """저장 대화상자(#32770) 핸들을 win32로 찾는다(모달에서도 확실)."""
    if win32gui is None:
        return None
    end = time.time() + timeout
    found = []

    def cb(h, _):
        try:
            if win32gui.IsWindowVisible(h) and win32gui.GetClassName(h) == "#32770":
                t = win32gui.GetWindowText(h)
                if ("저장" in t) or ("Save" in t) or ("이름" in t):
                    found.append(h)
        except Exception:
            pass
        return True

    while time.time() < end:
        found.clear()
        try:
            win32gui.EnumWindows(cb, None)
        except Exception:
            pass
        if found:
            return found[0]
        time.sleep(0.2)
    return None


def _cls(h):
    try:
        return win32gui.GetClassName(h)
    except Exception:
        return ""


def _all_children(hwnd):
    out = []

    def cb(h, _):
        out.append(h)
        return True

    try:
        win32gui.EnumChildWindows(hwnd, cb, None)
    except Exception:
        pass
    return out


def _dialog_filename_edit(dlg):
    """저장창의 파일이름 Edit 핸들. 모든 하위를 뒤져 ComboBox 안의 Edit 우선."""
    edits = []
    for h in _all_children(dlg):
        try:
            if win32gui.GetClassName(h) == "Edit":
                edits.append(h)
        except Exception:
            pass
    for h in edits:                       # 파일이름칸은 ComboBox 자식
        try:
            if "ComboBox" in win32gui.GetClassName(win32gui.GetParent(h)):
                return h
        except Exception:
            pass
    return edits[0] if edits else None


def _dialog_save_button(dlg):
    for h in _all_children(dlg):
        try:
            if win32gui.GetClassName(h) == "Button":
                t = win32gui.GetWindowText(h)
                if "저장" in t or "Save" in t:
                    return h
        except Exception:
            pass
    return None


def dismiss_export_popup(timeout=1.0):
    """카톡 '대화 내보내기 - 완료되었습니다' 팝업의 '확인'을 눌러 닫는다."""
    if win32gui is None:
        return False
    end = time.time() + timeout
    while time.time() < end:
        targets = []

        def cb(h, _):
            try:
                if win32gui.IsWindowVisible(h):
                    t = win32gui.GetWindowText(h)
                    if "내보내기" in t or "완료" in t:
                        targets.append(h)
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(cb, None)
        except Exception:
            pass
        for h in targets:
            btn = None
            for c in _all_children(h):
                try:
                    if _cls(c) == "Button" and "확인" in win32gui.GetWindowText(c):
                        btn = c
                        break
                except Exception:
                    pass
            if btn:
                try:
                    win32gui.SendMessage(btn, win32con.BM_CLICK, 0, 0)
                    return True
                except Exception:
                    pass
            try:                            # 버튼 못찾으면 기본버튼(확인)에 Enter
                win32gui.SetForegroundWindow(h)
                time.sleep(0.1)
                auto.SendKeys("{Enter}")
                return True
            except Exception:
                pass
        time.sleep(0.2)
    return False


def export_room(win, cfg):
    """방 창에서 Ctrl+S(대화 내보내기) -> 저장창을 win32로 제어해 txt 저장 -> 내용 반환."""
    dwell = cfg.get("dwell_ms", 700) / 1000.0
    tmp = HERE / "_export_tmp.txt"        # ASCII 경로
    try:
        if tmp.exists():
            tmp.unlink()
    except Exception:
        pass

    try:
        win.SetActive()
        time.sleep(dwell)
        auto.SendKeys("{Ctrl}(s)")
        time.sleep(dwell)
    except Exception as e:
        print(f"  Ctrl+S 오류: {e}")
        return None

    if win32gui is None:
        print("  pywin32 미설치 - 1_install.bat 을 다시 실행하세요")
        return None

    hwnd = find_save_dialog_hwnd(cfg.get("dialog_timeout", 12))
    if hwnd is None:
        print("  저장창을 못 찾음")
        return None

    # 저장창의 파일명칸(포커스+전체선택 상태)에 키보드로 전체 경로 입력 -> Enter 저장
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(0.4)
    try:
        auto.SendKeys("{Ctrl}(a)")
        time.sleep(0.15)
        auto.SendKeys(str(tmp).replace(" ", "{Space}"), waitTime=0.005)
        time.sleep(0.25)
        auto.SendKeys("{Enter}")                  # 저장
    except Exception as e:
        print(f"  파일명 입력/저장 오류: {e}")
        return None

    # 파일 생성 대기
    end = time.time() + cfg.get("save_timeout", 15)
    while time.time() < end:
        if tmp.exists() and tmp.stat().st_size > 0:
            break
        time.sleep(0.3)

    # 카톡 '완료' 팝업 확인 누르기(커스텀 창이라 블라인드 Enter)
    time.sleep(0.4)
    try:
        auto.SendKeys("{Enter}")
    except Exception:
        pass
    time.sleep(0.3)

    if not (tmp.exists() and tmp.stat().st_size > 0):
        print("  내보내기 파일이 지정 경로에 없음(경로 입력 실패 가능)")
        return None
    time.sleep(0.2)
    txt = _read_smart(tmp)
    if not cfg.get("export_keep", False):
        try:
            tmp.unlink()
        except Exception:
            pass
    return txt


def parse_clip(text, room, today):
    rows = []
    cur_date = today
    cur = None
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        s = line.strip()
        dm = DATE_RE.match(s.strip("- ").strip())   # 내보내기 '--- 날짜 ---' 도 처리
        if dm:
            y, mo, d = dm.groups()
            cur_date = f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
            continue
        mm = MSG_RE.match(line)
        if mm:
            if cur:
                rows.append(cur)
            sender, ampm, hh, mi, content = mm.groups()
            cur = {"room": room, "sender": sender,
                   "sent_at": f"{cur_date} {ampm} {int(hh)}:{mi}", "content": content}
        else:
            if s == "":
                continue
            if cur is not None:
                cur["content"] += "\n" + line
    if cur:
        rows.append(cur)
    return rows


def store(conn, rows, room, iso):
    new = db.insert_many(conn, rows, iso) if rows else 0
    if db.touch_room(conn, room, iso, new):
        print(f"  [새 방 감지] {room}")
        try:
            with (HERE / "new_rooms.log").open("a", encoding="utf-8") as f:
                f.write(f"{iso}\t{room}\n")
        except Exception:
            pass
    if new:
        print(f"  [{room}] 신규 {new}건")
    return new


# ── 모드: windows ───────────────────────────────────────
def run_windows(cfg, conn, iso, today):
    wins = chat_windows_by_handle()
    if not wins:
        print("  열린 대화방 창이 없음 - 방을 더블클릭해 창으로 띄우세요")
        return {"kakao_running": True, "rooms_opened": 0, "new_messages": 0,
                "export_failures": 0, "note": "열린 창 없음"}
    dwell = cfg.get("dwell_ms", 700) / 1000.0
    read_method = cfg.get("read_method", "export")
    total_new = 0
    export_fail = 0
    for _, w in wins.items():
        room = (w.Name or "").strip()
        text = export_room(w, cfg) if read_method == "export" else clip_read(w, dwell)
        if not text:
            export_fail += 1
            continue
        total_new += store(conn, parse_clip(text, room, today), room, iso)
    return {"kakao_running": True, "rooms_opened": len(wins), "new_messages": total_new,
            "export_failures": export_fail, "note": ""}


# ── 모드: cycle ─────────────────────────────────────────
def run_cycle(cfg, conn, iso, today):
    method = cfg.get("cycle_method", "keys")
    if method == "pixel":
        return run_cycle_pixel(cfg, conn, iso, today)
    return run_cycle_keys(cfg, conn, iso, today)


# ── cycle: 키보드 순회(기본, 권장) ───────────────────────
def run_cycle_keys(cfg, conn, iso, today):
    main = get_main_window()
    if main is None:
        print("  카카오톡 메인 창을 못 찾음(실행/로그인 확인)")
        return {"kakao_running": False, "rooms_opened": 0, "new_messages": 0,
                "export_failures": 0, "note": "카톡 메인창 없음"}
    chat = find_class(main, "EVA_VH_ListControl_Dblclk")
    if chat is None:
        print("  채팅목록을 못 찾음")
        return {"kakao_running": True, "rooms_opened": 0, "new_messages": 0,
                "export_failures": 0, "note": "채팅목록 못찾음(카톡 UI 변경 의심)"}
    dwell = cfg.get("dwell_ms", 700) / 1000.0
    max_rooms = cfg.get("max_rooms", 600)
    read_method = cfg.get("read_method", "export")   # export=Ctrl+S(권장) / clipboard
    try:
        main.SetActive()
        time.sleep(dwell)
        chat.SetFocus()          # 마우스 없이 목록에 키보드 포커스(선택 안 바뀜)
        time.sleep(0.3)
        auto.SendKeys("{Home}")  # 목록 맨 위로
        time.sleep(0.4)
    except Exception as e:
        print(f"  목록 포커스 오류: {e}")
        return

    seen = set()
    last = None
    stagnant = 0
    total_new = 0
    export_fail = 0
    for i in range(max_rooms):
        before = set(chat_windows_by_handle().keys())
        try:
            chat.SetFocus()
            time.sleep(0.1)
            auto.SendKeys("{Enter}")      # 선택된 방 열기
            time.sleep(dwell)
        except Exception:
            pass
        after = chat_windows_by_handle()
        newh = [h for h in after if h not in before]
        room = None
        if newh:
            handle = newh[0]
            win = after[handle]
            room = (win.Name or "").strip()
            if room and room not in seen:
                seen.add(room)
                if read_method == "export":
                    text = export_room(win, cfg)
                else:
                    text = clip_read(win, dwell)
                if text:
                    total_new += store(conn, parse_clip(text, room, today), room, iso)
                else:
                    export_fail += 1     # 창은 열렸는데 내보내기/읽기 실패
                print(f"  [{len(seen)}] {room} 읽고닫음")
            close_window(win)
            wait_closed(handle)
        else:
            print(f"  [{i}] 새 창 안 열림")

        try:                              # 다음 방으로
            main.SetActive()
            time.sleep(0.15)
            chat.SetFocus()
            time.sleep(0.1)
            auto.SendKeys("{Down}")
            time.sleep(0.2)
        except Exception:
            pass

        if room is None or room == last:
            stagnant += 1
        else:
            stagnant = 0
            last = room
        if stagnant >= 3:
            print(f"  더 진행 안 됨 -> 이번 바퀴 종료 (총 {len(seen)}개 방)")
            break

    for h, w in chat_windows_by_handle().items():
        if close_window(w):
            wait_closed(h, 1.0)

    return {"kakao_running": True, "rooms_opened": len(seen), "new_messages": total_new,
            "export_failures": export_fail, "note": ""}


# ── cycle: 마우스 좌표 순회(대체용) ─────────────────────
def run_cycle_pixel(cfg, conn, iso, today):
    if _U32 is None:
        print("  마우스 제어 불가(Windows 아님)")
        return
    main = get_main_window()
    if main is None:
        print("  카카오톡 메인 창을 못 찾음(실행/로그인 확인)")
        return
    try:
        main.SetActive()
    except Exception:
        pass
    dwell = cfg.get("dwell_ms", 700) / 1000.0
    time.sleep(dwell)

    chat = find_class(main, "EVA_VH_ListControl_Dblclk")
    if chat is None:
        print("  채팅목록을 못 찾음")
        return
    try:
        r = chat.BoundingRectangle
        left, top, right, bottom = r.left, r.top, r.right, r.bottom
    except Exception as e:
        print(f"  목록 좌표 오류: {e}")
        return

    row_h = cfg.get("row_height", 62)
    top_pad = cfg.get("list_top_pad", 6)
    cx = (left + right) // 2 - 15
    visible = max(1, int((bottom - top - top_pad) // row_h))
    max_scrolls = cfg.get("max_scrolls", 30)
    print(f"  목록 T{top}~B{bottom}, 행높이 {row_h}px, 보이는 행 ~{visible}")

    seen = set()
    stagnant = 0
    for sc in range(max_scrolls):
        new_this = 0
        for row in range(visible):
            y = top + top_pad + int(row_h * row + row_h * 0.5)
            if y >= bottom - 2:
                break
            before = set(chat_windows_by_handle().keys())
            pixel_double_click(cx, y)
            time.sleep(dwell)
            after = chat_windows_by_handle()
            newh = [h for h in after if h not in before]
            if not newh:
                continue
            handle = newh[0]
            win = after[handle]
            room = (win.Name or "").strip()
            if not room or room in seen:
                close_window(win); wait_closed(handle)
                continue
            seen.add(room)
            new_this += 1
            txt = clip_read(win, dwell)
            if txt is not None:
                store(conn, parse_clip(txt, room, today), room, iso)
            close_window(win); wait_closed(handle)
            print(f"  [{len(seen)}] {room} 읽고닫음")

        pixel_wheel_down(cx, (top + bottom) // 2, max(1, visible // 2))
        time.sleep(dwell)
        if new_this == 0:
            stagnant += 1
        else:
            stagnant = 0
        if stagnant >= 2:
            print(f"  더 이상 새 방 없음 -> 이번 바퀴 종료 (총 {len(seen)}개 방)")
            break

    for h, w in chat_windows_by_handle().items():   # 남은 창 정리
        if close_window(w):
            wait_closed(h, 1.0)


def evaluate(cfg, conn, stats):
    """이번 바퀴 결과로 상태 판정(ok/warn/error) + 커버리지 계산."""
    known = db.room_count(conn)
    opened = stats.get("rooms_opened", 0)
    coverage = round(opened / known, 2) if known else 1.0
    status, notes = "ok", []

    if not stats.get("kakao_running", True):
        status = "error"
        notes.append("카톡 미실행/로그아웃")
    elif stats.get("note"):
        status = "error"
        notes.append(stats["note"])
    else:
        cov_min = cfg.get("coverage_min_ratio", 0.7)
        # known 이 충분히 쌓인 뒤에만 커버리지 경고(초기엔 방 목록이 아직 안 참)
        if known >= 5 and coverage < cov_min:
            status = "warn"
            notes.append(f"커버리지 낮음 {opened}/{known}({coverage})")
        ef = stats.get("export_failures", 0)
        if ef and opened and ef >= max(3, opened * 0.3):
            status = "warn"
            notes.append(f"내보내기 실패 {ef}건")

    stats["known_rooms"] = known
    stats["coverage"] = coverage
    stats["status"] = status
    stats["note"] = "; ".join(notes)
    return stats


def main():
    cfg = load_config()
    conn = db.connect()
    mode = cfg.get("mode", "cycle")
    print(f"수집 시작 [mode={mode}] | dwell={cfg.get('dwell_ms',700)}ms | DB={db.DB_PATH.name}")
    print("Ctrl+C 로 종료.\n")
    prev_status = "ok"
    kakao_missing_streak = 0
    try:
        while True:
            now = datetime.now()
            iso = now.isoformat(timespec="seconds")
            today = now.strftime("%Y-%m-%d")
            stats = {"kakao_running": True, "rooms_opened": 0, "new_messages": 0,
                     "export_failures": 0, "note": ""}
            t0 = time.time()
            try:
                stats = run_cycle(cfg, conn, iso, today) if mode == "cycle" \
                    else run_windows(cfg, conn, iso, today)
                if not isinstance(stats, dict):
                    stats = {"kakao_running": True, "rooms_opened": 0, "new_messages": 0,
                             "export_failures": 0, "note": ""}
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"  [경고] 이번 주기 오류(무시하고 계속): {type(e).__name__}: {e}")
                stats = {"kakao_running": True, "rooms_opened": 0, "new_messages": 0,
                         "export_failures": 0, "note": f"예외 {type(e).__name__}: {e}", "error": True}

            stats["cycle_seconds"] = round(time.time() - t0, 1)
            evaluate(cfg, conn, stats)
            health.write_health(cfg, stats)

            # 카톡 미실행이 연속 지속되면 알림(일시적 재시작은 무시)
            if not stats.get("kakao_running", True):
                kakao_missing_streak += 1
            else:
                kakao_missing_streak = 0
            th = cfg.get("kakao_missing_alerts_after", 5)
            if kakao_missing_streak == th:
                alerts.notify(cfg, "CRITICAL", f"카톡이 {th}주기째 미실행/로그아웃 상태 — 수집 중단됨")

            # 상태가 나빠지는 전환에서만 알림(스팸 방지)
            rank = {"ok": 0, "warn": 1, "error": 2}
            if rank.get(stats["status"], 0) > rank.get(prev_status, 0):
                lvl = "CRITICAL" if stats["status"] == "error" else "WARN"
                if stats.get("kakao_running", True):   # 카톡미실행은 위에서 별도 처리
                    alerts.notify(cfg, lvl, f"수집 상태 {stats['status']}: {stats['note']}")
            prev_status = stats["status"]

            time.sleep(cfg.get("poll_seconds", 5))
    except KeyboardInterrupt:
        print("\n종료.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
