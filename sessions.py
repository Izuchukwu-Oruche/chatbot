from config import table
import time

def load_session(wa_id: str) -> dict:
    r = table.get_item(Key={"wa_id": wa_id})
    return r.get("Item") or {"wa_id": wa_id, "state":"idle", "slots":{}, "missing_slots": []}

def save_session(item: dict, ttl_minutes: int = 60):
    now = int(time.time())
    item["updated_at"] = now
    item["ttl"] = now + ttl_minutes*60
    table.put_item(Item=item)

def merge_slots(old: dict, new: dict) -> dict:
    out = dict(old or {})
    for k,v in (new or {}).items():
        out[k] = v
    return out