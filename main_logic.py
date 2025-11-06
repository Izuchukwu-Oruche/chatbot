"""
Conversation/session logic for the WhatsApp banking bot.

Responsibilities:
  - Manage a short-lived DynamoDB session (language, intent, slots)
  - Call the LLM parser to update state
  - Decide whether to ask for more info or fulfill an action
  - Format the final one-liner in the user's language
"""
from __future__ import annotations

import time
from decimal import Decimal
from typing import Any, Dict

from sessions import load_session, merge_slots, save_session
from llm import llm_parse, llm_one_liner
from whatsapp_helpers import wa_send_text
from banking_adapter import check_balance_adapter, transfer_adapter

IDLE_RESET_SECONDS = 60  # reset session silently after inactivity


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _ensure_defaults(sess: dict) -> dict:
    if "intent" not in sess:
        sess["intent"] = "unknown"
    if "lang" not in sess:
        sess["lang"] = "en"
    if "slots" not in sess:
        sess["slots"] = {}
    if "missing_slots" not in sess:
        sess["missing_slots"] = []
    return sess


def _session_age_seconds(sess: dict) -> int:
    try:
        updated = int(sess.get("updated_at") or 0)
        return max(0, int(time.time()) - updated)
    except Exception:
        return 0


def _amount_value(slots: dict) -> int:
    amt = slots.get("amount")
    if isinstance(amt, dict):
        return int(amt.get("value") or 0)
    if isinstance(amt, (int, float)):
        return int(amt)
    return 0


# ---------------------------------------------------------------------------
# Core entrypoint
# ---------------------------------------------------------------------------

def handle_text(from_id: str, text: str) -> None:
    """
    Main per-message handler. Stateless other than the short DynamoDB session.
    """
    sess = _ensure_defaults(load_session(from_id))

    # Silent inactivity reset
    if _session_age_seconds(sess) > IDLE_RESET_SECONDS:
        sess = {
            "wa_id": from_id,
            "state": "idle",
            "intent": "unknown",
            "lang": sess.get("lang", "auto"),
            "slots": {},
            "missing_slots": [],
        }
        save_session(sess)

    # Use auto language on first turn; afterwards, stick to session language
    preferred = (
        "auto"
        if (sess.get("intent", "unknown") == "unknown" and not (sess.get("slots") or {}))
        else (sess.get("lang") or "auto")
    )

    parsed = llm_parse(
        text,
        prev_intent=sess.get("intent", "unknown"),
        prev_slots=sess.get("slots") or {},
        preferred_lang=preferred,
    )

    new_intent = parsed.get("intent") or "unknown"
    lang = (parsed.get("lang") or {}).get("detected") or (sess.get("lang") or "en")
    sess["lang"] = lang

    new_slots = parsed.get("slots") or {}
    sess["slots"] = merge_slots(sess.get("slots") or {}, new_slots)
    sess["intent"] = new_intent

    action = (parsed.get("action") or "ask").lower()
    ask_slot = parsed.get("ask_slot")
    reply = (parsed.get("reply") or "").strip() or "Okay."

    # Reset / cancel
    if action == "reset" or new_intent == "reset":
        sess = {"wa_id": from_id, "state": "idle", "intent": "unknown", "lang": lang, "slots": {}, "missing_slots": []}
        save_session(sess)
        wa_send_text(from_id, reply)
        return

    # Ask for more information
    if action == "ask" or ask_slot:
        sess["missing_slots"] = parsed.get("missing_slots") or []
        save_session(sess)
        wa_send_text(from_id, reply)
        return

    # Fulfill (side-effects)
    if action == "fulfill":
        intent = new_intent
        if intent == "check_balance":
            res = check_balance_adapter(from_id, sess["slots"])
            try:
                bal = Decimal(str(res.get("balance", "0")))
                base = f"Your current balance is NGN {bal:,.2f}."
            except Exception:
                base = f"Your current balance is NGN {res.get('balance', '0')}."
            final = llm_one_liner(lang, base)

        elif intent == "transfer":
            # Normalize amount to plain int for the adapter
            sess["slots"]["amount"] = _amount_value(sess["slots"]) or sess["slots"].get("amount")
            res = transfer_adapter(from_id, sess["slots"])
            if res.get("ok"):
                txid = res.get("transaction_id", "?")
                base = f"Transfer successful. Reference {txid}."
            else:
                base = f"Transfer failed: {res.get('error', 'unknown error')}."
            final = llm_one_liner(lang, base)

        else:
            final = llm_one_liner(lang, "I am not sure how to help with that.")

        wa_send_text(from_id, final)
        # Always return to a clean idle session after fulfillment
        sess = {"wa_id": from_id, "state": "idle", "intent": "unknown", "lang": lang, "slots": {}, "missing_slots": []}
        save_session(sess)
        return

    # Default: persist updated session and echo parsed reply
    save_session(sess)
    wa_send_text(from_id, reply)
