from __future__ import annotations

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

from .config import settings
from .database import Database
from .gmail_client import GmailClient
from .logging_setup import setup_logging
from .processor import EmailProcessor
from .auth import ensure_users_interactive, load_users, verify_user
from .accounts import ensure_accounts_interactive, load_accounts

setup_logging()

app = FastAPI(title="Gmail AI Assistant")

ensure_users_interactive()
ensure_accounts_interactive()

_db = Database()
_accounts = load_accounts()
_gmail_clients = {a.name: GmailClient(a.credentials_file, a.token_file, a.user_id) for a in _accounts}
_processors = {a.name: EmailProcessor(_gmail_clients[a.name], _db, a.name) for a in _accounts}

basic_auth = HTTPBasic()


def require_basic_auth(credentials: HTTPBasicCredentials = Depends(basic_auth)):
    users = load_users()
    if not users:
        raise HTTPException(status_code=401, detail="No users configured")
    if not verify_user(credentials.username, credentials.password, users):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health", dependencies=[Depends(require_basic_auth)])
def health():
    return {"status": "ok", "accounts": list(_processors.keys())}


@app.post("/run-scan", dependencies=[Depends(require_basic_auth)])
def run_scan(account: str | None = None):
    if account:
        if account not in _processors:
            raise HTTPException(status_code=404, detail="Account not found")
        return _processors[account].scan_and_process()
    # scan all
    return {name: p.scan_and_process() for name, p in _processors.items()}


@app.get("/emails/recent", dependencies=[Depends(require_basic_auth)])
def emails_recent(limit: int = 50):
    return _db.recent_actions(limit=limit)


@app.get("/actions/logs", dependencies=[Depends(require_basic_auth)])
def actions_logs(limit: int = 50):
    return _db.recent_actions(limit=limit)


@app.get("/stats", dependencies=[Depends(require_basic_auth)])
def stats():
    return _db.stats()


@app.get("/rules", dependencies=[Depends(require_basic_auth)])
def rules():
    return {
        "junk_threshold": settings.JUNK_CONFIDENCE_THRESHOLD,
        "important_threshold": settings.IMPORTANT_CONFIDENCE_THRESHOLD,
        "cleanup_mode": settings.CLEANUP_MODE,
    }


@app.post("/rules/update", dependencies=[Depends(require_basic_auth)])
def rules_update(junk_threshold: float | None = None, cleanup_mode: str | None = None):
    # This endpoint just echoes updates; persistent config should be done via .env
    return {
        "junk_threshold": junk_threshold or settings.JUNK_CONFIDENCE_THRESHOLD,
        "cleanup_mode": cleanup_mode or settings.CLEANUP_MODE,
    }


@app.get("/manual-review", dependencies=[Depends(require_basic_auth)])
def manual_review(limit: int = 50):
    return _db.list_manual_review(limit=limit)


@app.post("/manual-review/{email_id}/keep", dependencies=[Depends(require_basic_auth)])
def manual_keep(email_id: str, account: str):
    try:
        if account not in _gmail_clients:
            raise HTTPException(status_code=404, detail="Account not found")
        _gmail_clients[account].add_label(email_id, "important_ai")
        _db.remove_manual_review(account, email_id)
        return {"status": "kept"}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/manual-review/{email_id}/junk", dependencies=[Depends(require_basic_auth)])
def manual_junk(email_id: str, account: str):
    try:
        if account not in _gmail_clients:
            raise HTTPException(status_code=404, detail="Account not found")
        if settings.CLEANUP_MODE == "delete":
            _gmail_clients[account].trash(email_id)
        elif settings.CLEANUP_MODE == "spam":
            _gmail_clients[account].spam(email_id)
        else:
            _gmail_clients[account].archive(email_id)
        _db.remove_manual_review(account, email_id)
        return {"status": "junked"}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))
