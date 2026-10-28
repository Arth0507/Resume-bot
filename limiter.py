import time
from collections import defaultdict, deque

from fastapi import HTTPException

_hits = defaultdict(deque)


def check(key: str, limit: int, window: int = 60):
    """Ek key (jaise user) ko 'window' seconds me 'limit' se zyada requests nahi karne deta."""
    now = time.time()
    q = _hits[key]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        wait = int(window - (now - q[0])) + 1
        raise HTTPException(429, f"Too many requests. Please wait {wait} seconds and try again.")
    q.append(now)