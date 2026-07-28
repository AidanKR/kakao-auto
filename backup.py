"""
DB 백업(회전) + 선택적 암호화 — ④보안.

- SQLite 온라인 백업 API로 안전 사본(수집 중에도 OK) → gzip → (패스프레이즈 있으면)암호화
- backups/ 에 회전 보관(최근 N개), 공유폴더(클라우드)에도 복사(옵션)
- 손상/실수/랜섬웨어 대비. 암호화하면 클라우드 유출 시에도 안전.

사용: python backup.py         (8_backup.bat / 스케줄러가 매일 호출)
"""
import argparse
import gzip
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import db
import cryptobox

HERE = Path(__file__).parent


def load_config():
    p = HERE / "config.json"
    if not p.exists():
        return {}
    data = p.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return json.loads(data.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            try:
                return json.loads(data.decode(enc).replace("\\", "/"))
            except Exception:
                continue
    return {}


def _rotate(folder, keep):
    files = sorted(folder.glob("kakao_*"))
    for old in files[:-keep] if keep > 0 else []:
        try:
            old.unlink()
        except Exception:
            pass


def make_backup(cfg=None):
    cfg = cfg or load_config()
    if not db.DB_PATH.exists():
        print("kakao.db 가 없습니다 — 백업할 것이 없음")
        return None
    backup_dir = Path(cfg.get("backup_dir") or (HERE / "backups")).expanduser()
    backup_dir.mkdir(parents=True, exist_ok=True)
    keep = cfg.get("backup_keep", 14)
    passphrase = cfg.get("backup_passphrase") or ""
    ts = datetime.now().strftime("%Y%m%d_%H%M")

    # 1) 안전 사본(온라인 백업) → 메모리로 읽어 gzip
    tmp = backup_dir / f"_tmp_{ts}.db"
    src = sqlite3.connect(db.DB_PATH)
    dst = sqlite3.connect(tmp)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    gz = gzip.compress(tmp.read_bytes())
    tmp.unlink()

    # 2) 암호화(패스프레이즈 있으면)
    if passphrase:
        if not cryptobox.available():
            print("[백업] 패스프레이즈 설정됐지만 cryptography 미설치 — pip install cryptography 후 재시도")
            return None
        blob = cryptobox.encrypt(gz, passphrase)
        ext = ".db.gz.enc"
    else:
        blob = gz
        ext = ".db.gz"

    out = backup_dir / f"kakao_{ts}{ext}"
    out.write_bytes(blob)
    tag = " [암호화]" if passphrase else ""
    print(f"[백업] 생성: {out.name} ({len(blob)//1024}KB){tag}")
    _rotate(backup_dir, keep)

    # 3) 공유폴더(클라우드)에도 복사(옵션)
    if cfg.get("backup_to_share", True) and cfg.get("share_dir"):
        try:
            sdb = Path(cfg["share_dir"]) / "backups"
            sdb.mkdir(parents=True, exist_ok=True)
            shutil.copy2(out, sdb / out.name)
            _rotate(sdb, keep)
            print(f"[백업] 공유폴더 복사: {sdb/out.name}")
        except Exception as e:
            print(f"[백업] 공유폴더 복사 실패(무시): {e}")

    if not passphrase:
        print("  ⚠ 백업이 평문입니다. 클라우드 유출 대비하려면 config 'backup_passphrase' 설정(암호화).")
    return out


if __name__ == "__main__":
    argparse.ArgumentParser(description="kakao.db 백업").parse_args()
    make_backup()
