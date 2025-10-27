import time

def check_balance_adapter(wa_id: str, slots: dict) -> dict:
    # Minimal stub — replace with your internal call.
    # Optionally use BANK_API_BASE/BANK_API_TOKEN here.
    # Return shape: {"ok": True, "balance": 50000}
    return {"ok": True, "balance": 50000}

def transfer_adapter(wa_id: str, slots: dict) -> dict:
    # REQUIRED: amount.value, destination_account, destination_bank, recipient_name
    amt = slots.get("amount",{}).get("value")
    acct = slots.get("destination_account")
    bank = slots.get("destination_bank")
    rec  = slots.get("recipient_name")
    if not all([amt, acct, bank, rec]):
        return {"ok": False, "error": "missing fields"}
    # Demo success. Replace with real HTTP call, handle otp_provided if needed.
    return {"ok": True, "transaction_id": "TX-"+str(int(time.time()))}