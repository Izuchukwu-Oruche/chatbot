"""
WhatsApp helper utilities for replying and extracting inbound messages.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict, List

from config import GRAPH_API_VERSION, PHONE_NUMBER_ID, WHATSAPP_TOKEN


def wa_ok(body: str = "OK", status: int = 200) -> Dict[str, Any]:
    """
    Build a simple Lambda-friendly HTTP response.
    """
    return {"statusCode": status, "headers": {"Content-Type": "text/plain"}, "body": body}


def wa_send_text(to: str, body: str) -> None:
    """
    Send a text message via WhatsApp Cloud API.

    Parameters
    ----------
    to : str
        WhatsApp phone number id for the recipient.
    body : str
        Message body (truncated to 4000 chars by the API).
    """
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body[:4000]},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        _ = r.read()


def extract_messages(event_body: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Extract plain text messages from the WhatsApp webhook body.

    Returns a list of {'from': str, 'text': str}.
    """
    msgs: list[dict[str, str]] = []
    for entry in event_body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for m in value.get("messages", []) or []:
                if m.get("type") == "text" and "from" in m:
                    msgs.append({"from": m["from"], "text": (m["text"]["body"] or "").strip()})
    return msgs
