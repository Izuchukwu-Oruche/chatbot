# --- top of file ---
from sessions import load_session, merge_slots, save_session
from llm import llm_parse, llm_confirm
from whatsapp_helpers import wa_send_text
from banking_adapter import check_balance_adapter, transfer_adapter
import re  # NEW

# NEW: simple detectors and localized prompts
VERNACULARS = {"pcm","ig","yo","ha"}
BANK_NAMES = {
    "GTBANK","GTB","ACCESS","ACCESS BANK","UBA","ZENITH","FIRST BANK","FIDELITY",
    "FCMB","POLARIS","STERLING","WEMA","JAIZ","PROVIDUS","UNION","UNITY","OPAY","PALMPAY"
}

def _is_language_neutral(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    up = t.upper()
    # digits, punctuation, or pure numbers with spacing
    if re.fullmatch(r"[\s\d.,-]+", t):
        return True
    # bank-only messages frequently appear during transfers
    if up in BANK_NAMES:
        return True
    # mostly digits, no letters
    letters = sum(ch.isalpha() for ch in t)
    digits  = sum(ch.isdigit() for ch in t)
    return letters == 0 and digits > 0

def _pick_effective_lang(prev: str, detected: str, confidence: float, text: str) -> str:
    """
    Make language sticky: if we were in a vernacular, don't switch to 'en'
    on neutral/low-confidence turns.
    """
    prev = (prev or "").strip() or None
    detected = (detected or "en").strip()
    confidence = float(confidence or 0.0)

    if prev in VERNACULARS:
        if detected == "en" or confidence < 0.80 or _is_language_neutral(text):
            return prev
    return detected or prev or "en"

LOCALIZED_ASK = {
    "en": {
        "amount": "How much should I send? (e.g., ₦5000)",
        "destination_account": "What is the destination account number?",
        "destination_bank": "Which bank?",
        "recipient_name": "Who is the recipient?",
        "narration": "Add a short note?",
        "source_account": "Which source account should I use?",
        "otp_provided": "Please provide the OTP."
    },
    "pcm": {
        "amount": "How much make I send? (e.g. ₦5000)",
        "destination_account": "Wetin be the account number?",
        "destination_bank": "Which bank?",
        "recipient_name": "Who go receive am?",
        "narration": "You wan add small note?",
        "source_account": "Which account make I use send am?",
        "otp_provided": "Abeg send the OTP."
    },
    "ig": {
        "amount": "Ego ole ka m ziga? (dịka ₦5000)",
        "destination_account": "Kedu nọmba akaụntụ?",
        "destination_bank": "Bankị gị chọrọ bụ nkee?",
        "recipient_name": "Ònye ga-anata ego?",
        "narration": "Tinye obere nkọwa?",
        "source_account": "Kedu akaụntụ ka m jiri ziga?",
        "otp_provided": "Biko zipu OTP."
    },
    "yo": {
        "amount": "Elo ni kí n rán? (gẹ́gẹ́ bi ₦5000)",
        "destination_account": "Kini nómba àkàǹtì tí a máa rán sí?",
        "destination_bank": "Ile-ifowopamọ́ wo?",
        "recipient_name": "Ta ni olùgbà?",
        "narration": "Ṣe k'á fi akọsilẹ́ kékeré kun?",
        "source_account": "Àkàǹtì wo ni kí n lo?",
        "otp_provided": "Jọ̀wọ́ fi OTP ranṣẹ́."
    },
    "ha": {
        "amount": "Naira nawa zan tura? (misali ₦5000)",
        "destination_account": "Menene lambar asusun da za a tura?",
        "destination_bank": "Wane banki?",
        "recipient_name": "Waɗe sunan mai karɓa?",
        "narration": "A saka ƙaramin bayani?",
        "source_account": "Wane asusu zan yi amfani da shi?",
        "otp_provided": "Don Allah a turo OTP."
    }
}

def _localized_ask(lang: str, slot: str) -> str:
    lang = lang if lang in LOCALIZED_ASK else "en"
    return LOCALIZED_ASK[lang].get(slot, LOCALIZED_ASK[lang]["amount"])

def handle_text(from_id: str, text: str):
    sess = load_session(from_id)
    parsed = llm_parse(text)

    detected_lang = parsed.get("lang",{}).get("detected","en")
    detected_conf = parsed.get("lang",{}).get("confidence",0.0)
    # NEW: choose sticky/effective language
    lang = _pick_effective_lang(sess.get("lang"), detected_lang, detected_conf, text)

    intent    = parsed.get("intent","unknown")
    slots_new = parsed.get("slots",{}) or {}
    missing   = parsed.get("missing_slots",[]) or []
    ask_slot  = parsed.get("ask_slot","none")
    # NOTE: we ignore LLM ask_user to avoid English fallback; we'll localize ourselves.
    canonical = parsed.get("canonical_en","")
    ready     = bool(parsed.get("ready_for_fulfillment", False))

    # Merge with session state
    sess["lang"]   = lang  # NEW: save the effective language
    sess["intent"] = sess.get("intent") or intent
    if sess["intent"] == "unknown" and intent != "unknown":
        sess["intent"] = intent
    sess["slots"]  = merge_slots(sess.get("slots"), slots_new)

    # Recompute missing
    still_missing = [s for s in missing if not sess["slots"].get(s)]
    sess["missing_slots"] = still_missing
    sess["state"] = "in_progress"

    # Ask for next required slot (always in the sticky language)
    if not ready or still_missing:
        if not ask_slot or ask_slot == "none":
            ask_slot = still_missing[0] if still_missing else "amount"
        ask_user = _localized_ask(lang, ask_slot)
        save_session(sess)
        wa_send_text(from_id, ask_user)
        return

    # Ready for fulfillment
    outcome_en = ""
    if sess["intent"] == "check_balance":
        res = check_balance_adapter(from_id, sess["slots"])
        outcome_en = f"Balance is NGN {res['balance']:,}." if res.get("ok") else "Could not retrieve balance."
    elif sess["intent"] == "transfer":
        res = transfer_adapter(from_id, sess["slots"])
        outcome_en = (f"Transfer successful (ID {res['transaction_id']})."
                      if res.get("ok") else f"Transfer failed: {res.get('error','unknown error')}.")
    else:
        outcome_en = "I’m not sure how to help with that."

    # Localized one-line confirmation in the sticky language
    confirm = llm_confirm(lang, canonical, outcome_en)
    wa_send_text(from_id, confirm)

    # Reset session
    sess["state"] = "idle"
    sess["intent"] = "unknown"
    sess["slots"] = {}
    sess["missing_slots"] = []
    save_session(sess)
