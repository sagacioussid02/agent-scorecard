"""Approval requests for side-effecting tools."""
import hashlib
import hmac
import time

SECRET = b"from-env-in-real-life"


def request_approval(action: dict, approver_id: str, ttl: int = 900) -> dict:
    payload = repr(sorted(action.items())).encode()
    signature = hmac.new(SECRET, payload, hashlib.sha256).hexdigest()
    return {"action": action, "signature": signature, "expires_at": time.time() + ttl, "approver_id": approver_id}


def check_approval(record: dict, action: dict) -> bool:
    if time.time() > record["expires_at"]:
        return False  # expired approvals are rejected: deny by default
    payload = repr(sorted(action.items())).encode()
    expected = hmac.new(SECRET, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, record["signature"])


def record_decision(store, record: dict, approved_by: str, approved: bool) -> None:
    store.append({"approved_by": approved_by, "approved": approved, "approved_at": time.time(), **record})
