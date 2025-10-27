from sessions import load_session, merge_slots, save_session
from llm import llm_parse, llm_confirm
from whatsapp_helpers import wa_send_text
from banking_adapter import check_balance_adapter, transfer_adapter

def handle_text(from_id: str, text: str):
    sess = load_session(from_id)
    parsed = llm_parse(text)

    lang      = parsed.get("lang",{}).get("detected","en")
    intent    = parsed.get("intent","unknown")
    slots_new = parsed.get("slots",{}) or {}
    missing   = parsed.get("missing_slots",[]) or []
    ask_slot  = parsed.get("ask_slot","none")
    ask_user  = parsed.get("ask_user","")
    canonical = parsed.get("canonical_en","")
    ready     = bool(parsed.get("ready_for_fulfillment", False))

    # Merge with session state
    sess["lang"]   = lang
    sess["intent"] = sess.get("intent") or intent  # keep first intent if already set
    if sess["intent"] == "unknown" and intent != "unknown":
        sess["intent"] = intent
    sess["slots"]  = merge_slots(sess.get("slots"), slots_new)

    # Recompute missing: prefer LLM's view but remove any slot we already have
    still_missing = [s for s in missing if not sess["slots"].get(s)]
    sess["missing_slots"] = still_missing
    sess["state"] = "in_progress"

    # If not ready → ask for the next missing slot (ask_user from LLM)
    if not ready or still_missing:
        # safety fallback if ask_user empty
        if not ask_user:
            ask_map = {
              "amount":"How much should I send? (e.g., ₦5000)",
              "destination_account":"What is the destination account number?",
              "destination_bank":"Which bank?",
              "recipient_name":"Who is the recipient?",
              "narration":"Add a short note?",
              "source_account":"Which source account should I use?",
              "otp_provided":"Please provide the OTP."
            }
            ask_user = ask_map.get(ask_slot, "Please provide the missing details.")
        save_session(sess)
        wa_send_text(from_id, ask_user)
        return

    # Ready for fulfillment
    outcome_en = ""
    if sess["intent"] == "check_balance":
        res = check_balance_adapter(from_id, sess["slots"])
        if res.get("ok"):
            outcome_en = f"Balance is NGN {res['balance']:,}."
        else:
            outcome_en = "Could not retrieve balance."
    elif sess["intent"] == "transfer":
        res = transfer_adapter(from_id, sess["slots"])
        if res.get("ok"):
            outcome_en = f"Transfer successful (ID {res['transaction_id']})."
        else:
            outcome_en = f"Transfer failed: {res.get('error','unknown error')}."
    else:
        outcome_en = "I’m not sure how to help with that."

    # Localized one-line confirmation
    confirm = llm_confirm(lang, canonical, outcome_en)
    wa_send_text(from_id, confirm)

    # Reset/keep session
    sess["state"] = "idle"
    sess["intent"] = "unknown"
    sess["slots"] = {}
    sess["missing_slots"] = []
    save_session(sess)