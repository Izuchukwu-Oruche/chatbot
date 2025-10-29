from sessions import load_session, merge_slots, save_session
from llm import llm_parse, llm_confirm
from whatsapp_helpers import wa_send_text
from banking_adapter import check_balance_adapter, transfer_adapter
import re

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
    if re.fullmatch(r"[\s\d.,-]+", t):
        return True
    if up in BANK_NAMES:
        return True
    letters = sum(ch.isalpha() for ch in t)
    digits  = sum(ch.isdigit() for ch in t)
    return letters == 0 and digits > 0

def _pick_effective_lang(prev: str, detected: str, confidence: float, text: str) -> str:
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
        "destination_account_number": "What is the beneficiary account number?",
        "destination_bank": "Which bank? (e.g., GTBank, Zenith)",
        "recipient_name": "Who is the recipient?",
        "narration": "Add a short note?",
        "source_account_number": "Which source account number should I use?",
        "source_account_name": "What is the source account name?",
        "pin": "Please provide your 4‑digit PIN.",
    },
    "pcm": {
        "amount": "How much make I send? (e.g. ₦5000)",
        "destination_account_number": "Wetin be the account number?",
        "destination_bank": "Which bank? (e.g. GTBank, Zenith)",
        "recipient_name": "Who go receive am?",
        "narration": "You wan add small note?",
        "source_account_number": "Which account make I use send am?",
        "source_account_name": "Wetín be the account name?",
        "pin": "Abeg send your 4‑digit PIN.",
    },
    "ig": {
        "amount": "Ego ole ka m ziga? (dịka ₦5000)",
        "destination_account_number": "Kedu nọmba akaụntụ?",
        "destination_bank": "Bankị gị chọrọ bụ nkee?",
        "recipient_name": "Ònye ga-anata ego?",
        "narration": "Tinye obere nkọwa?",
        "source_account_number": "Kedu akaụntụ ka m jiri ziga?",
        "source_account_name": "Gịnị bụ aha akaụntụ isi?",
        "pin": "Biko zipu PIN nke gị (nọmba 4).",
    },
    "yo": {
        "amount": "Èló ni kí n rán? (gẹ́gẹ́ bi ₦5000)",
        "destination_account_number": "Kini nómba àkàǹtì olùgbà?",
        "destination_bank": "Ile-ifowopamọ́ wo? (bí GTBank, Zenith)",
        "recipient_name": "Ta ni olùgbà?",
        "narration": "Ṣe k'á fi akọsilẹ́ díẹ̀ kun?",
        "source_account_number": "Àkàǹtì wo ni kí n lo?",
        "source_account_name": "Kini orúkọ àkàǹtì ìsanwó?",
        "pin": "Jọ̀wọ́, fi PIN rẹ (ọ̀nà mẹ́rin) ranṣẹ́.",
    },
    "ha": {
        "amount": "Nawa zan tura? (misali ₦5000)",
        "destination_account_number": "Menene lambar asusun mai karɓa?",
        "destination_bank": "Wane banki? (misali GTBank, Zenith)",
        "recipient_name": "Waɗe sunan mai karɓa?",
        "narration": "A saka ƙaramin bayani?",
        "source_account_number": "Wane asusu zan yi amfani da shi?",
        "source_account_name": "Menene sunan asusun asali?",
        "pin": "Don Allah a turo PIN ɗinka (4 lambobi).",
    }
}

def _ask(lang: str, slot: str) -> str:
    lang = lang if lang in LOCALIZED_ASK else "en"
    d = LOCALIZED_ASK[lang]
    return d.get(slot, d["amount"])

def _next_missing(intent: str, slots: dict, suggested_missing: list) -> str:
    # Our minimal requirements for MVP
    if intent == "check_balance":
        req = ["source_account_number", "pin"]
    elif intent == "transfer":
        req = ["amount", "recipient_name", "destination_account_number",
               "destination_bank", "source_account_number", "source_account_name", "pin"]
    else:
        return suggested_missing[0] if suggested_missing else "amount"
    for s in req:
        if s not in slots or not slots.get(s):
            return s
    return ""

def handle_text(from_id: str, text: str):
    sess = load_session(from_id)
    parsed = llm_parse(text)

    detected_lang = parsed.get("lang",{}).get("detected","en")
    detected_conf = parsed.get("lang",{}).get("confidence",0.0)
    lang = _pick_effective_lang(sess.get("lang"), detected_lang, detected_conf, text)

    intent    = parsed.get("intent","unknown")
    slots_new = parsed.get("slots",{}) or {}
    canonical = parsed.get("canonical_en","")
    suggested_missing = parsed.get("missing_slots",[]) or []

    # Merge with session
    sess["lang"] = lang
    sess["intent"] = sess.get("intent") or intent
    if sess["intent"] == "unknown" and intent != "unknown":
        sess["intent"] = intent
    sess["slots"] = merge_slots(sess.get("slots"), slots_new)

    # Decide next slot
    ask_slot = _next_missing(sess["intent"], sess["slots"], suggested_missing)
    if ask_slot:
        save_session(sess)
        wa_send_text(from_id, _ask(lang, ask_slot))
        return

    # Fulfill
    if sess["intent"] == "check_balance":
        res = check_balance_adapter(from_id, sess["slots"])
        if res.get("ok"):
            outcome_en = f"Balance is NGN {res['balance']:,}."
        else:
            outcome_en = f"Could not retrieve balance: {res.get('error','unknown')}."
    elif sess["intent"] == "transfer":
        res = transfer_adapter(from_id, sess["slots"])
        if res.get("ok"):
            outcome_en = f"Transfer successful (ID {res.get('transaction_id','?')})."
        else:
            outcome_en = f"Transfer failed: {res.get('error','unknown error')}."
    else:
        outcome_en = "I’m not sure how to help with that."

    # Confirmation
    confirm = llm_confirm(lang, canonical, outcome_en)
    wa_send_text(from_id, confirm)

    # Reset session
    sess["state"] = "idle"
    sess["intent"] = "unknown"
    sess["slots"] = {}
    sess["missing_slots"] = []
    save_session(sess)
