# auth.py
from __future__ import annotations
import json, os, secrets, string, time, hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional

APP_NAME = "DigitaleAlchemyStudio"

def app_data_dir() -> Path:
    # Windows: %APPDATA%\DigitaleAlchemyStudio
    appdata = os.getenv("APPDATA")
    if appdata:
        p = Path(appdata) / APP_NAME
    else:
        # Fallback für Linux/macOS
        p = Path.home() / ".local" / "state" / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p

DATA_DIR = app_data_dir()
USERS_FILE = DATA_DIR / "users.json"
CONFIG_FILE = DATA_DIR / "config.json"

# ---------------- Password hashing (PBKDF2) ----------------

def _pbkdf2(password: str, salt: bytes, iterations: int = 130_000) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return dk.hex()

def hash_password(password: str, salt: Optional[bytes] = None) -> Dict[str, str]:
    salt = salt or secrets.token_bytes(16)
    return {
        "algo": "pbkdf2_sha256",
        "iters": 130_000,
        "salt": salt.hex(),
        "hash": _pbkdf2(password, salt)
    }

def verify_password(password: str, rec: Dict[str, str]) -> bool:
    if rec.get("algo") != "pbkdf2_sha256":
        return False
    salt = bytes.fromhex(rec["salt"])
    iters = int(rec.get("iters", 130_000))
    return _pbkdf2(password, salt, iters) == rec["hash"]

# ---------------- Data models ----------------

@dataclass
class User:
    username: str
    password: Dict[str, str]         # hashed
    roles: list
    must_change_pw: bool = False
    tokens: list = None              # for remember-me tokens (hashes)
    failed: int = 0                  # failed attempts
    lock_until: float = 0.0          # unix timestamp

    def to_dict(self):
        d = asdict(self)
        if d.get("tokens") is None:
            d["tokens"] = []
        return d

# ---------------- Storage helpers ----------------

def load_users() -> Dict[str, User]:
    if not USERS_FILE.exists():
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    users: Dict[str, User] = {}
    for name, ud in raw.items():
        users[name] = User(**ud)
    return users

def save_users(users: Dict[str, User]):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({k: u.to_dict() for k, u in users.items()}, f, indent=2, ensure_ascii=False)

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

# ---------------- Bootstrap (first run) ----------------

def ensure_default_admin(users: Dict[str, User]) -> Dict[str, User]:
    if "admin" in users:
        return users
    pwd = "admin"  # bewusst einfach für Erststart; erfordert Passwortwechsel
    users["admin"] = User(
        username="admin",
        password=hash_password(pwd),
        roles=["admin"],
        must_change_pw=True,
        tokens=[]
    )
    save_users(users)
    return users

# ---------------- Remember-me tokens ----------------

def new_remember_token() -> str:
    # 43 Zeichen URL-sicher ~ 256 bit
    return secrets.token_urlsafe(32)

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def attach_token(users: Dict[str, User], username: str, token: str):
    u = users[username]
    th = token_hash(token)
    if u.tokens is None:
        u.tokens = []
    # max 5 gültige Tokens pro User
    u.tokens = (u.tokens + [th])[-5:]
    save_users(users)

def verify_token(users: Dict[str, User], username: str, token: str) -> bool:
    u = users.get(username)
    if not u or not u.tokens:
        return False
    return token_hash(token) in u.tokens

# ---------------- Auth flow ----------------

LOCK_MINUTES = 5
MAX_FAILED = 5

def authenticate(username: str, password: str) -> tuple[bool, str]:
    users = load_users()
    users = ensure_default_admin(users)

    u = users.get(username)
    now = time.time()
    if not u:
        return False, "Unbekannter Benutzer."

    # Lockout
    if u.lock_until and now < u.lock_until:
        mins = int((u.lock_until - now) // 60) + 1
        return False, f"Konto gesperrt. Bitte in {mins} Min. erneut versuchen."

    ok = verify_password(password, u.password)
    if ok:
        u.failed = 0
        u.lock_until = 0
        save_users(users)
        return True, ""
    else:
        u.failed = (u.failed or 0) + 1
        if u.failed >= MAX_FAILED:
            u.lock_until = now + LOCK_MINUTES * 60
            u.failed = 0
        save_users(users)
        return False, "Passwort falsch."

def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    users = load_users()
    u = users.get(username)
    if not u:
        return False, "Benutzer existiert nicht."

    if not verify_password(old_password, u.password):
        return False, "Altes Passwort stimmt nicht."

    if not validate_new_password(new_password):
        return False, "Neues Passwort erfüllt die Mindestanforderungen nicht."

    u.password = hash_password(new_password)
    u.must_change_pw = False
    save_users(users)
    return True, "Passwort geändert."

def validate_new_password(pw: str) -> bool:
    # Minimum Regeln – kannst du bei Bedarf verschärfen
    if len(pw) < 8:
        return False
    csets = [any(ch.islower() for ch in pw),
             any(ch.isupper() for ch in pw),
             any(ch.isdigit() for ch in pw),
             any(ch in "!@#$%^&*()-_=+[]{};:,.<>?/\\|" for ch in pw)]
    return sum(1 for c in csets if c) >= 3
