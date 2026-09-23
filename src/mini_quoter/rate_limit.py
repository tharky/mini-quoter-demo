import datetime
from zoneinfo import ZoneInfo

import streamlit as st

LIMIT = 3
TZ = ZoneInfo("America/Chicago")


@st.cache_resource
def _store() -> dict[str, int]:
    return {}


def _seconds_to_midnight() -> int:
    now = datetime.datetime.now(TZ)
    tomorrow = (now + datetime.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int((tomorrow - now).total_seconds())


def _key_for(uid: str) -> str:
    today = datetime.datetime.now(TZ).strftime("%Y%m%d")
    return f"{today}:{uid}"


def check(uid: str):
    """Return the current quota state without consuming a request."""
    store = _store()
    key = _key_for(uid)
    used = store.get(key, 0)
    allowed = used < LIMIT
    return allowed, used, max(LIMIT - used, 0), _seconds_to_midnight()


def take(uid: str):
    """Consume one request if quota remains."""
    allowed, used, _, reset = check(uid)
    if not allowed:
        return False, used, 0, reset

    store = _store()
    key = _key_for(uid)
    store[key] = used + 1
    used = store[key]
    return True, used, LIMIT - used, reset
