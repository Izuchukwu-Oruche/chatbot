"""
AWS Lambda entrypoint for WhatsApp webhook.

- GET  : Facebook/WhatsApp webhook verification
- POST : Inbound message processing (text only)
"""
from __future__ import annotations

import json
from typing import Any, Dict

from config import VERIFY_TOKEN
from whatsapp_helpers import wa_ok, extract_messages
from main_logic import handle_text


def _handle_get(event: Dict[str, Any]):
    """
    Handle verification handshake from WhatsApp/Meta.
    """
    params = event.get("queryStringParameters") or {}
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return wa_ok(params.get("hub.challenge", ""), 200)
    return wa_ok("forbidden", 403)


def _handle_post(event: Dict[str, Any]):
    """
    Handle inbound messages from WhatsApp. We only process text messages.
    """
    try:
        body = json.loads(event.get("body") or "{}")
    except Exception:
        return wa_ok("bad request", 400)

    if body.get("object") != "whatsapp_business_account":
        return wa_ok("ignored", 200)

    for msg in extract_messages(body):
        try:
            handle_text(msg["from"], msg["text"])
        except Exception as e:
            # Avoid raising to Meta; log and continue
            print("ERR handle_text:", e)
    return wa_ok("ok", 200)


def lambda_handler(event, context):
    """
    Lambda runtime entrypoint.
    """
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod", "GET")
    )

    if method == "GET":
        return _handle_get(event)

    if method == "POST":
        return _handle_post(event)

    return wa_ok("method not allowed", 405)
