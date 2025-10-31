import time, base64
import requests
from typing import Optional, Dict, Any
from config import ACCOUNT_ID, FLK_STAGE, PHONE_COUNTRY_CODE, PHONE_NUMBER

BASE_URL = "https://api-dev.finlake.tech/mobility"
TIMEOUT = 15

def _headers(auth_token: Optional[str] = None) -> Dict[str, str]:
    h = {
        "Content-Type": "application/json",
        "X-Account-Id": ACCOUNT_ID,
        "X-Flk-Stage": FLK_STAGE,
    }
    if auth_token:
        h["Authorization"] = f"Bearer {auth_token}"
    return h

def generate_credentials(transaction_pin: str) -> Dict[str, str]:
    signature = f"{int(time.time())}:chatbot"
    sig = base64.b64encode(signature.encode()).decode()
    return {
        "phoneCountryCode": PHONE_COUNTRY_CODE,
        "phoneNumber": PHONE_NUMBER,
        "requestSignature": sig,
        "transactionPin": transaction_pin or "",
    }

def _post(path: str, payload: Dict[str, Any], auth_token: Optional[str] = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    # print(_headers(auth_token))
    r = requests.post(url, json=payload, headers=_headers(auth_token), timeout=TIMEOUT)
    try:
        data = r.json()
    except ValueError:
        raise Exception(f"Finlake non-JSON response {r.status_code}: {r.text[:300]}")
    if r.status_code != 200:
        raise Exception(f"Finlake HTTP {r.status_code}: {data}")
    # Common envelope check
    if isinstance(data, dict) and data.get("responseCode") not in (None, "", "00"):
        # Some endpoints return '00' foress succ
        raise Exception(f"Finlake error responseCode={data.get('responseCode')} message={data.get('responseMessage')}")
    return data

# ---- Public endpoints (chatbot-controller) ----

def list_banks(transaction_pin: str) -> Dict[str, Any]:
    payload = generate_credentials(transaction_pin)
    return _post("/public/read/cts-bank", payload)

def internal_name_enquiry(account_number: str, transaction_pin: str) -> Dict[str, Any]:
    payload = {
            "accountNumber": account_number,
            "credentials": generate_credentials(transaction_pin),
        }
    return _post("/public/read/cts-internal-name-enquiry", payload)

def transaction_history_by_account(account_number: str, start_date: str, end_date: str,
                                   page: int, page_size: int, transaction_pin: str) -> Dict[str, Any]:
    payload = {
        "accountNumber": account_number,
        "credentials": generate_credentials(transaction_pin),
        "startDate": start_date,
        "endDate": end_date,
        "page": page,
        "pageSize": page_size
    }
    return _post("/public/read/cts-by-account-number", payload)

def get_balance(account_number: str, transaction_pin: str):
    """
    Returns Decimal-like string (2dp) for the current balance.
    We DO NOT coerce to int; we preserve the decimal part.
    """
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
    today = time.strftime("%Y-%m-%d")
    month_ago = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 30*24*3600))
    data = transaction_history_by_account(account_number, month_ago, today, page=1, page_size=1,
                                          transaction_pin=transaction_pin)
    acct = (data.get("account") or [{}])[0]
    bal_str = str(acct.get("accountBalance") or "0")
    try:
        dec = Decimal(bal_str)
        dec = dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return str(dec)
    except (InvalidOperation, Exception):
        return "0.00"


def fund_transfer_internal(*, amount: int, credit_account_name: str, credit_account_number: str,
                           debit_account_name: str, debit_account_number: str, location: str = "NGA",
                           narration: str = "", save_beneficiary: bool = True,
                           transaction_pin: str) -> Dict[str, Any]:
    payload = {
        
            "amount": str(amount),
            "credentials": generate_credentials(transaction_pin),
            "creditAccountName": credit_account_name,
            "creditAccountNumber": credit_account_number,
            "debitAccountName": debit_account_name,
            "debitAccountNumber": debit_account_number,
            "location": location,
            "narration": narration or "",
            "saveBeneficiary": bool(save_beneficiary),
            "transactionPin": transaction_pin,
        
    }
    return _post("/public/create/cts-internal-fund-transfer", payload)

def fund_transfer_outward(*, amount: int, credit_account_name: str, credit_account_number: str,
                          credit_bank_code: str, credit_bank_name: str,
                          debit_account_name: str, debit_account_number: str,
                          location: str = "NGA", name_enquiry_reference: str = "", narration: str = "",
                          save_beneficiary: bool = True, transaction_pin: str) -> Dict[str, Any]:
    payload = {
        
            "amount": str(amount),
            "credentials": generate_credentials(transaction_pin),
            "creditAccountName": credit_account_name,
            "creditAccountNumber": credit_account_number,
            "creditBankCode": credit_bank_code,
            "creditBankName": credit_bank_name,
            "debitAccountName": debit_account_name,
            "debitAccountNumber": debit_account_number,
            "location": location,
            "nameEnquiryReference": name_enquiry_reference or "",
            "narration": narration or "",
            "saveBeneficiary": bool(save_beneficiary),
            "transactionPin": transaction_pin,
        
    }
    return _post("/public/create/cts-outward-fund-transfer", payload)

def user_info(transaction_pin: str) -> Dict[str, Any]:
    """
    Chatbot Controller:
      POST /public/read/cts-user-info

    Body shape (per spec):
      { "botCredentialsRequest": { phoneCountryCode, phoneNumber, requestSignature, transactionPin } }
    """
    payload = generate_credentials(transaction_pin)
    
    return _post("/public/read/cts-user-info", payload)
