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

def take(uid: str):
    s = _store()
    k = _key_for(uid)
    used = s.get(k, 0)
    if used >= LIMIT:
        return False, used, 0, _seconds_to_midnight()
    s[k] = used + 1
    used = s[k]
    return True, used, LIMIT - used, _seconds_to_midnight()
