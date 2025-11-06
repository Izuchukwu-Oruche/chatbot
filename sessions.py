"""
Session storage on DynamoDB.

We keep a minimal user session with:
  - wa_id (partition key)
  - state / intent / lang
  - slots / missing_slots
  - updated_at (epoch seconds)
  - ttl (auto-expiry)
"""
from __future__ import annotations

import time
from typing import Dict, Any

from config import table


def load_session(wa_id: str) -> dict:
    """
    Fetch the session for a given WhatsApp user id, or a default shell.
    """
    r = table.get_item(Key={"wa_id": wa_id})
    return r.get("Item") or {"wa_id": wa_id, "state": "idle", "slots": {}, "missing_slots": []}


def save_session(item: dict, ttl_minutes: int = 60) -> None:
    """
    Upsert the session and set an expiry TTL.
    """
    now = int(time.time())
    item["updated_at"] = now
    item["ttl"] = now + ttl_minutes * 60
    table.put_item(Item=item)


def merge_slots(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """
    Shallow-merge slot dictionaries; new keys override.
    """
    out = dict(old or {})
    for k, v in (new or {}).items():
        out[k] = v
    return out
