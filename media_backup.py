"""
사진·파일 만료 전 백업(캐시 수집) — 카톡 최대 불만 '사진 저장기간 만료' 대응.

원리(정직하게):
  카톡 PC가 이미 '다운로드/캐시한' 미디어 파일을 뒤져서 우리 아카이브로 복사한다(중복 제거).
  → 카톡이 서버에서 지우기 전에 로컬에 있던 사진·파일을 안전하게 보존.

⚠ 한계(반드시 이해):
  - '아직 안 본(다운로드 안 된)' 미디어는 이 방법으로 못 가져옵니다. 그건 열어봐야 다운로드됨.
    (자동 클릭은 불안정/위험해서 기본 미포함) → 자주 돌릴수록 더 많이 건집니다.
  - 카톡 캐시 폴더 위치·형식은 버전마다 다릅니다. 처음엔 어떤 폴더를 뒤졌는지 로그를 보고
    config 의 media_dirs 를 맞춰주세요.

동작:
  후보 폴더(자동탐지 + config media_dirs) 를 훑어 이미지/영상/문서 확장자 파일을
  media_out(기본 share_dir/media/날짜/) 로 복사, sha1 해시로 중복 제거(media_index.txt).

사용: python media_backup.py            (기본)
      python media_backup.py --days 3   (최근 3일 수정분만)
"""
import argparse
import hashlib
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import briefing

HERE = __import__("appdir").APP_DIR
IMG_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic"}
EXTS = IMG_EXTS | {".mp4", ".mov", ".avi", ".mkv", ".m4a", ".mp3",
                  ".pdf", ".hwp", ".doc", ".docx", ".xls", ".xlsx",
                  ".ppt", ".pptx", ".zip"}
# 이모티콘/스티커는 보통 이런 이름의 캐시 폴더에 들어있고 크기가 작다.
EMOTICON_MARKERS = ["emoticon", "sticker", "이모티콘", "스티커",
                    "digitalitem", "spritecon", "theme"]


def candidate_dirs(cfg):
    dirs = [Path(p) for p in (cfg.get("media_dirs") or [])]
    up = os.environ.get("USERPROFILE") or str(Path.home())
    la = os.environ.get("LOCALAPPDATA", "")
    ad = os.environ.get("APPDATA", "")
    guesses = [
        Path(up) / "Documents" / "카카오톡 받은 파일",
        Path(up) / "Documents" / "KakaoTalk Downloads",
        Path(la) / "Kakao" / "KakaoTalk" if la else None,
        Path(ad) / "Kakao" / "KakaoTalk" if ad else None,
    ]
    for g in guesses:
        if g and g not in dirs:
            dirs.append(g)
    return [d for d in dirs if d.exists() and d.is_dir()]


def sha1_file(p, chunk=1 << 20):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def load_index(idx_path):
    if idx_path.exists():
        return set(idx_path.read_text(encoding="utf-8").split())
    return set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, help="최근 N일 수정분만(기본: 전체)")
    ap.add_argument("--out", help="미디어 저장 폴더")
    args = ap.parse_args()

    cfg = briefing.load_config()
    out = Path(args.out) if args.out else \
        Path(cfg.get("media_out") or (cfg.get("share_dir") or (HERE / "share")) ) / "media"
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)

    # 실제 이미지만(이모티콘/스티커 제외) 옵션
    image_only = bool(cfg.get("image_only", False))
    exts = set(cfg.get("media_exts") or (IMG_EXTS if image_only else EXTS))
    skip_emo = cfg.get("skip_emoticons", True)
    markers = [m.lower() for m in (cfg.get("emoticon_markers") or EMOTICON_MARKERS)]
    # 이모티콘/썸네일 걸러낼 최소 크기(이미지에만 적용). 0이면 크기필터 끔.
    min_bytes = int(cfg.get("media_min_bytes", 20000))

    cutoff = None
    if args.days:
        cutoff = (datetime.now() - timedelta(days=args.days)).timestamp()

    dirs = candidate_dirs(cfg)
    print("훑을 폴더:")
    for d in dirs:
        print("  -", d)
    if not dirs:
        print("  (없음) — config 의 media_dirs 에 카톡 받은파일/캐시 폴더 경로를 넣어주세요.")
        return

    idx_path = out / "media_index.txt"
    seen = load_index(idx_path)
    new_hashes = []
    copied = skipped = scanned = emoticon_skipped = 0

    for d in dirs:
        for root, _, files in os.walk(d):
            root_low = root.lower()
            # 이모티콘/스티커 캐시 폴더 통째로 건너뜀
            if skip_emo and any(m in root_low for m in markers):
                continue
            for fn in files:
                ext = Path(fn).suffix.lower()
                if ext not in exts:
                    continue
                src = Path(root) / fn
                if skip_emo and any(m in fn.lower() for m in markers):
                    emoticon_skipped += 1
                    continue
                try:
                    st = src.stat()
                except Exception:
                    continue
                if cutoff and st.st_mtime < cutoff:
                    continue
                # 실제 사진만: 너무 작은 이미지(이모티콘/썸네일)는 제외
                if skip_emo and min_bytes and ext in IMG_EXTS and st.st_size < min_bytes:
                    emoticon_skipped += 1
                    continue
                scanned += 1
                try:
                    h = sha1_file(src)
                except Exception:
                    continue
                if h in seen:
                    skipped += 1
                    continue
                day = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m")
                dest_dir = out / day
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / f"{h[:10]}_{fn}"
                try:
                    shutil.copy2(src, dest)
                    seen.add(h); new_hashes.append(h); copied += 1
                except Exception as e:
                    print(f"  복사 실패({src.name}): {e}")

    if new_hashes:
        with idx_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(new_hashes) + "\n")

    print(f"미디어 백업: 새로 {copied}개 복사 · 중복 {skipped} · 스캔 {scanned}"
          f" · 이모티콘/스티커 제외 {emoticon_skipped} → {out}")
    if copied == 0 and scanned == 0:
        print("  ⚠ 대상 파일을 못 찾음. 카톡 '받은 파일 저장 위치'를 config media_dirs 에 지정하세요.")


if __name__ == "__main__":
    main()
