"""
백업 복구 — 백업 파일(.db.gz 또는 .db.gz.enc)을 kakao.db 로 되살린다.

안전을 위해 기본은 'kakao_restored.db'로 풀고, 라이브 DB를 덮어쓰지 않는다.

사용:
  python restore.py backups/kakao_20260728_0200.db.gz.enc
  python restore.py <파일> --out kakao_restored.db
  python restore.py <파일> --pass "패스프레이즈"   (암호화 백업. 없으면 config backup_passphrase)
"""
import argparse
import gzip
import json
from pathlib import Path

import cryptobox

HERE = Path(__file__).parent


def load_config():
    p = HERE / "config.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_bytes().decode("utf-8-sig"))
    except Exception:
        try:
            return json.loads(p.read_bytes().decode("cp949"))
        except Exception:
            return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("backup", help="백업 파일 경로(.db.gz / .db.gz.enc)")
    ap.add_argument("--out", default="kakao_restored.db", help="복구 파일명(기본 kakao_restored.db)")
    ap.add_argument("--pass", dest="passphrase", default=None, help="암호화 백업의 패스프레이즈")
    args = ap.parse_args()

    blob = Path(args.backup).read_bytes()
    if cryptobox.is_encrypted(blob):
        pw = args.passphrase or load_config().get("backup_passphrase") or ""
        if not pw:
            print("암호화된 백업입니다. --pass 또는 config backup_passphrase 필요")
            return
        try:
            gz = cryptobox.decrypt(blob, pw)
        except Exception as e:
            print(f"복호화 실패(패스프레이즈 확인): {e}")
            return
    else:
        gz = blob

    try:
        raw = gzip.decompress(gz)
    except Exception as e:
        print(f"압축 해제 실패: {e}")
        return

    out = Path(args.out)
    out.write_bytes(raw)
    print(f"복구 완료: {out} ({len(raw)//1024}KB)")
    print("  확인 후 문제없으면 kakao.db 로 교체하세요(수집기 종료 상태에서).")


if __name__ == "__main__":
    main()
