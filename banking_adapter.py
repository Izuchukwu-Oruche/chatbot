"""
Bank action adapters used by the WhatsApp bot.

This module provides two public helpers:
  - `check_balance_adapter(...)`
  - `transfer_adapter(...)`

They normalize/validate slots from the NLU, talk to Finlake via `finlake.py`,
and return small dicts that the higher layer can format into user-facing text.

Notes
-----
* The Finlake bank list is cached in-process for 1 hour to reduce API calls.
* Keep signatures stable; other modules import these functions directly.
"""
from __future__ import annotations

import time
from typing import Dict, Any, Optional

import finlake

# ---------------------------------------------------------------------------
# Simple in-memory bank cache (process lifetime)
# ---------------------------------------------------------------------------

_BANKS: Optional[list[dict]] = None
_BANKS_AT: float = 0.0
_CACHE_TTL_SECONDS = 3600  # 1 hour


def _load_banks(pin: str) -> list[dict]:
    """
    Retrieve and cache the list of banks from Finlake.

    Parameters
    ----------
    pin : str
        Transaction PIN used in credential generation.

    Returns
    -------
    list[dict]
        The bank records as returned by Finlake.
    """
    global _BANKS, _BANKS_AT
    if _BANKS and (time.time() - _BANKS_AT) < _CACHE_TTL_SECONDS:
        return _BANKS

    try:
        data = finlake.list_banks(pin)
        _BANKS = data.get("data") or []
        _BANKS_AT = time.time()
    except Exception:
        # On failure, return an empty cache rather than raising (caller will handle)
        _BANKS, _BANKS_AT = [], time.time()
    return _BANKS


def _match_bank(bank_text: str, pin: str) -> Optional[dict]:
    """
    Try to match a user's destination bank text to a Finlake bank record.

    We compare against:
      * full name
      * short name
      * bank code
      * name/short name with spaces removed
      * startswith / contains fallbacks

    Returns a dict with 'code' and 'name' if a match is found, else None.
    """
    bank_text = (bank_text or "").strip().upper()
    if not bank_text:
        return None

    for b in _load_banks(pin):
        name = (b.get("bankName") or "").upper()
        short = (b.get("bankShortName") or "").upper()
        code = (b.get("bankCode") or "").upper()

        # Exact / normalized exact
        if bank_text in (name, short, code, short.replace(" ", ""), name.replace(" ", "")):
            return {"code": code, "name": b.get("bankName") or short or code}

        # Looser matching
        if bank_text in name or bank_text in short or name.startswith(bank_text) or short.startswith(bank_text):
            return {"code": code, "name": b.get("bankName") or short or code}

    return None


# ---------------------------------------------------------------------------
# Public adapters
# ---------------------------------------------------------------------------

def check_balance_adapter(wa_id: str, slots: Dict[str, Any]) -> Dict[str, Any]:
    """
    Look up a user's account balance via Finlake.

    Expected slots
    --------------
    - source_account_number | source_account
    - pin | transaction_pin

    Returns
    -------
    {"ok": True, "balance": "<decimal-string>"} on success,
    {"ok": False, "error": "<reason>"} on failure.
    """
    acct = slots.get("source_account_number") or slots.get("source_account")
    pin = slots.get("pin") or slots.get("transaction_pin") or ""
    if not acct or not pin:
        return {"ok": False, "error": "missing source_account_number or pin"}

    bal = finlake.get_balance(acct, pin)
    return {"ok": True, "balance": bal}


def transfer_adapter(wa_id: str, slots: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform either an internal (same bank) or outward fund transfer.

    Expected slots
    --------------
    - amount (int or {"value": int})
    - destination_account_number | destination_account
    - destination_bank | credit_bank_name (optional; if present and matched -> outward)
    - recipient_name | credit_account_name
    - source_account_number | debit_account_number
    - source_account_name | debit_account_name (optional; defaults to "You")
    - narration (optional)
    - pin | transaction_pin

    Returns
    -------
    {"ok": True, "transaction_id": "..."} on success,
    {"ok": False, "error": "<reason>"} on failure.
    """
    # Normalize amount
    amt_obj = slots.get("amount")
    amount = amt_obj.get("value") if isinstance(amt_obj, dict) else amt_obj
    try:
        amount = int(amount or 0)
    except Exception:
        amount = 0

    dst_acct = slots.get("destination_account_number") or slots.get("destination_account")
    dst_bank = slots.get("destination_bank") or slots.get("credit_bank_name")
    recipient = slots.get("recipient_name") or slots.get("credit_account_name")
    src_acct = slots.get("source_account_number") or slots.get("debit_account_number")
    src_name = slots.get("source_account_name") or slots.get("debit_account_name") or "You"
    narration = slots.get("narration", "") or ""
    pin = slots.get("pin") or slots.get("transaction_pin") or ""

    if not all([amount, dst_acct, recipient, src_acct, pin]):
        return {"ok": False, "error": "missing fields"}

    # Decide internal vs outward based on bank match
    bank_match = _match_bank(dst_bank or "", pin) if dst_bank else None

    if bank_match:
        # Outward transfer
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
        # Internal (same bank)
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
