import time
from typing import Dict, Any
import finlake

# Simple in-memory bank cache (process lifetime)
_BANKS = None
_BANKS_AT = 0

def _load_banks(pin: str):
    global _BANKS, _BANKS_AT
    if _BANKS and (time.time() - _BANKS_AT) < 3600:
        return _BANKS
    try:
        data = finlake.list_banks(pin)
        _BANKS = data.get("data") or []
        _BANKS_AT = time.time()
    except Exception:
        _BANKS, _BANKS_AT = [], time.time()
    return _BANKS

def _match_bank(bank_text: str, pin: str):
    bank_text = (bank_text or "").strip().upper()
    if not bank_text:
        return None
    for b in _load_banks(pin):
        name = (b.get("bankName") or "").upper()
        short = (b.get("bankShortName") or "").upper()
        code = b.get("bankCode") or ""
        if bank_text in (name, short, code, short.replace(" ", ""), name.replace(" ", "")):
            return {"code": code, "name": b.get("bankName") or short or code}
        # loose startswith/contains
        if bank_text in name or bank_text in short or name.startswith(bank_text) or short.startswith(bank_text):
            return {"code": code, "name": b.get("bankName") or short or code}
    return None

def check_balance_adapter(wa_id: str, slots: Dict[str, Any]) -> Dict[str, Any]:
    acct = slots.get("source_account_number") or slots.get("source_account")
    pin  = slots.get("pin") or slots.get("transaction_pin") or ""
    if not acct or not pin:
        return {"ok": False, "error": "missing source_account_number or pin"}
    bal = finlake.get_balance(acct, pin)
    return {"ok": True, "balance": bal}

def transfer_adapter(wa_id: str, slots: Dict[str, Any]) -> Dict[str, Any]:
    # Normalize inputs
    amount = slots.get("amount",{}).get("value") if isinstance(slots.get("amount"), dict) else slots.get("amount")
    amount = int(amount or 0)
    dst_acct = slots.get("destination_account_number") or slots.get("destination_account")
    dst_bank = slots.get("destination_bank") or slots.get("credit_bank_name")
    recipient = slots.get("recipient_name") or slots.get("credit_account_name")
    src_acct = slots.get("source_account_number") or slots.get("debit_account_number")
    src_name = slots.get("source_account_name") or slots.get("debit_account_name") or "You"
    narration = slots.get("narration","")
    pin = slots.get("pin") or slots.get("transaction_pin") or ""

    if not all([amount, dst_acct, recipient, src_acct, pin]):
        return {"ok": False, "error": "missing fields"}

    # Decide internal vs outward
    bank_match = _match_bank(dst_bank or "", pin) if dst_bank else None

    if bank_match:
        # outward
        out = finlake.fund_transfer_outward(
            amount=amount,
            credit_account_name=recipient,
            credit_account_number=dst_acct,
            credit_bank_code=bank_match["code"],
            credit_bank_name=bank_match["name"],
            debit_account_name=src_name,
            debit_account_number=src_acct,
            narration=narration,
            transaction_pin=pin,
            save_beneficiary=True,
        )
        txid = out.get("transactionId") or out.get("paymentReference") or out.get("reference")
        return {"ok": True, "transaction_id": txid}
    else:
        # internal (same bank)
        out = finlake.fund_transfer_internal(
            amount=amount,
            credit_account_name=recipient,
            credit_account_number=dst_acct,
            debit_account_name=src_name,
            debit_account_number=src_acct,
            narration=narration,
            transaction_pin=pin,
            save_beneficiary=True,
        )
        txid = out.get("reference") or out.get("cbaReference")
        return {"ok": True, "transaction_id": txid}
