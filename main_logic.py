from sessions import load_session, merge_slots, save_session
from llm import llm_parse, llm_one_liner
from whatsapp_helpers import wa_send_text
from banking_adapter import check_balance_adapter, transfer_adapter
import time

IDLE_RESET_SECONDS = 60  # can be made env-configurable if needed

def _ensure_defaults(sess: dict):
    if "intent" not in sess: sess["intent"] = "unknown"
    if "lang" not in sess:   sess["lang"]   = "en"
    if "slots" not in sess:  sess["slots"]  = {}
    if "missing_slots" not in sess: sess["missing_slots"] = []
    return sess

def _session_age_seconds(sess: dict) -> int:
    try:
        updated = int(sess.get("updated_at") or 0)
        return max(0, int(time.time()) - updated)
    except Exception:
        return 0

def _amount_value(slots: dict):
    amt = slots.get("amount")
    if isinstance(amt, dict):
        return int(amt.get("value") or 0)
    if isinstance(amt, (int, float)):
        return int(amt)
    return 0

def handle_text(from_id: str, text: str):
    sess = _ensure_defaults(load_session(from_id))

    # Inactivity reset (LLM generates the notice line)
    if _session_age_seconds(sess) > IDLE_RESET_SECONDS:
        notice = llm_one_liner(sess.get("lang","en"), "Your previous session expired due to inactivity. I've reset it. What would you like to do?")
        sess = {"wa_id": from_id, "state":"idle", "intent":"unknown", "lang": sess.get("lang","en"), "slots":{}, "missing_slots": []}
        save_session(sess)
        wa_send_text(from_id, notice)
        return

    # LLM-driven parse+policy (pure LLM)
    parsed = llm_parse(text, prev_intent=sess.get("intent","unknown"), prev_slots=sess.get("slots") or {})

    # Merge state from LLM (intent/lang)
    new_intent = parsed.get("intent") or "unknown"
    lang = (parsed.get("lang") or {}).get("detected") or sess.get("lang") or "en"
    sess["lang"] = lang

    # slots: merge previous then overwrite with LLM-proposed (merge behavior should be LLM-driven)
    new_slots = parsed.get("slots") or {}
    sess["slots"] = merge_slots(sess.get("slots") or {}, new_slots)
    sess["intent"] = new_intent

    action = (parsed.get("action") or "ask").lower()
    ask_slot = parsed.get("ask_slot")
    reply = (parsed.get("reply") or "").strip() or "Okay."

    if action == "reset" or new_intent == "reset":
        # Reset and send the LLM's reply
        sess = {"wa_id": from_id, "state":"idle", "intent":"unknown", "lang": lang, "slots":{}, "missing_slots": []}
        save_session(sess)
        wa_send_text(from_id, reply)
        return

    # Ask branch
    if action == "ask" or ask_slot:
        sess["missing_slots"] = parsed.get("missing_slots") or []
        save_session(sess)
        wa_send_text(from_id, reply)
        return

    # Fulfill branch
    if action == "fulfill":
        intent = new_intent
        if intent == "check_balance":
            res = check_balance_adapter(from_id, sess["slots"])
            if res.get("ok"):
                final = llm_one_liner(lang, f"Balance is NGN {res['balance']:,}.")
            else:
                final = llm_one_liner(lang, f"Could not retrieve balance: {res.get('error','unknown')}.")
        elif intent == "transfer":
            # Make sure amount becomes int
            sess["slots"]["amount"] = _amount_value(sess["slots"]) or sess["slots"].get("amount")
            res = transfer_adapter(from_id, sess["slots"])
            if res.get("ok"):
                txid = res.get("transaction_id","?")
                final = llm_one_liner(lang, f"Transfer successful. Reference {txid}.")
            else:
                final = llm_one_liner(lang, f"Transfer failed: {res.get('error','unknown error')}.")
        else:
            final = llm_one_liner(lang, "I’m not sure how to help with that.")

        wa_send_text(from_id, final)
        # Always reset after fulfillment
        sess = {"wa_id": from_id, "state":"idle", "intent":"unknown", "lang": lang, "slots":{}, "missing_slots": []}
        save_session(sess)
        return

    # Fallback: just echo the LLM reply and keep session
    save_session(sess)
    wa_send_text(from_id, reply)
