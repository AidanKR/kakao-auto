"""
백업 암호화(선택) — 패스프레이즈 기반 AES(Fernet) + PBKDF2.

형식: MAGIC(4) + salt(16) + Fernet토큰
`cryptography` 라이브러리 필요(윈도우 pip 설치 간단). 미설치 시 available()=False.
"""
import base64
import os

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    _OK = True
except Exception:
    _OK = False

MAGIC = b"KAB1"
_ITER = 200_000


def available():
    return _OK


def _key(passphrase, salt):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=_ITER)
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def encrypt(data, passphrase):
    if not _OK:
        raise RuntimeError("cryptography 미설치 — pip install cryptography")
    salt = os.urandom(16)
    token = Fernet(_key(passphrase, salt)).encrypt(data)
    return MAGIC + salt + token


def is_encrypted(blob):
    return blob[:4] == MAGIC


def decrypt(blob, passphrase):
    if not _OK:
        raise RuntimeError("cryptography 미설치 — pip install cryptography")
    if not is_encrypted(blob):
        raise ValueError("암호화 형식이 아닙니다")
    salt, token = blob[4:20], blob[20:]
    return Fernet(_key(passphrase, salt)).decrypt(token)
