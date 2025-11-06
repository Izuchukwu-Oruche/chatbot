"""
Finlake API wrapper used by the WhatsApp bot.

Only small, explicit helpers are exposed and each returns parsed JSON
(or raises an Exception with a concise message on failure).

Includes simple HTTP retries with exponential backoff for transient errors.
"""
from __future__ import annotations

import base64
import time
import random
from typing import Optional, Dict, Any

import requests
from requests.exceptions import Timeout, ConnectionError, RequestException

from config import ACCOUNT_ID, FLK_STAGE, PHONE_COUNTRY_CODE, PHONE_NUMBER

BASE_URL = "https://api-dev.finlake.tech/mobility"
TIMEOUT = 15  # seconds

# Retry policy (simple, conservative)
MAX_RETRIES = 3
BACKOFF_BASE = 0.6  # seconds; exponential (0.6, 1.2, 2.4) + small jitter

# Keep a session for connection pooling
_SESSION = requests.Session()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _headers(auth_token: Optional[str] = None) -> Dict[str, str]:
    """
    Build Finlake headers, optionally including Authorization.
    """
    h = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Account-Id": ACCOUNT_ID,
        "X-Flk-Stage": FLK_STAGE,
    }
    if auth_token:
        h["Authorization"] = f"Bearer {auth_token}"
    return h


def generate_credentials(transaction_pin: str) -> Dict[str, str]:
    """
    Finlake "credentials" payload for public endpoints.

    The requestSignature must be Base64 of "<unix_ts>:chatbot".
    """
    signature = f"{int(time.time())}:chatbot"
    sig = base64.b64encode(signature.encode()).decode()
    return {
        "phoneCountryCode": PHONE_COUNTRY_CODE,
        "phoneNumber": PHONE_NUMBER,
        "requestSignature": sig,
        "transactionPin": transaction_pin or "",
    }


def _post(path: str, payload: Dict[str, Any], auth_token: Optional[str] = None) -> Dict[str, Any]:
    """
    POST helper with simple retries for transient failures.

    Retries on: network errors (timeout/connection), and HTTP {429, 500, 502, 503, 504}.
    Envelope errors are treated as business errors and are NOT retried.
    """
    url = f"{BASE_URL}{path}"
    last_err: Optional[Exception] = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = _SESSION.post(url, json=payload, headers=_headers(auth_token), timeout=TIMEOUT)
            status = r.status_code

            # Retry on transient HTTP codes
            if status in (429, 500, 502, 503, 504):
                last_err = Exception(f"Finlake HTTP {status}: {r.text[:300]}")
                if attempt < MAX_RETRIES:
                    sleep_s = BACKOFF_BASE * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
                    time.sleep(sleep_s)
                    continue

            # Parse JSON (or raise if not JSON)
            try:
                data = r.json()
            except ValueError:
                raise Exception(f"Finlake non-JSON response {status}: {r.text[:300]}")

            # Non-200 that isn't in our retry list -> raise immediately
            if status != 200:
                raise Exception(f"Finlake HTTP {status}: {data}")

            # Common envelope check (do NOT retry)
            if isinstance(data, dict) and data.get("responseCode") not in (None, "", "00"):
                # Some endpoints use '00' for success
                raise Exception(
                    f"Finlake error responseCode={data.get('responseCode')} "
                    f"message={data.get('responseMessage')}"
                )

            return data

        except (Timeout, ConnectionError) as e:
            last_err = e
            if attempt < MAX_RETRIES:
                sleep_s = BACKOFF_BASE * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
                time.sleep(sleep_s)
                continue
        except RequestException as e:
            last_err = e
            if attempt < MAX_RETRIES:
                sleep_s = BACKOFF_BASE * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
                time.sleep(sleep_s)
                continue

    raise Exception(f"Finlake request failed after {MAX_RETRIES} attempts: {last_err}")

# ---------------------------------------------------------------------------
# Public endpoints (chatbot-controller)
# ---------------------------------------------------------------------------

def list_banks(transaction_pin: str) -> Dict[str, Any]:
    payload = generate_credentials(transaction_pin)
    return _post("/public/read/cts-bank", payload)


def internal_name_enquiry(account_number: str, transaction_pin: str) -> Dict[str, Any]:
    payload = {
        "accountNumber": account_number,
        "credentials": generate_credentials(transaction_pin),
    }
    return _post("/public/read/cts-internal-name-enquiry", payload)


def transaction_history_by_account(
    account_number: str,
    start_date: str,
    end_date: str,
    page: int,
    page_size: int,
    transaction_pin: str,
) -> Dict[str, Any]:
    payload = {
        "accountNumber": account_number,
        "credentials": generate_credentials(transaction_pin),
        "startDate": start_date,
        "endDate": end_date,
        "page": page,
        "pageSize": page_size,
    }
    return _post("/public/read/cts-by-account-number", payload)


def get_balance(account_number: str, transaction_pin: str) -> str:
    """
    Returns a decimal string (2 d.p.) representing the current balance.

    We preserve and return a string to avoid Decimal serialization issues upstream.
    """
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

    today = time.strftime("%Y-%m-%d")
    month_ago = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 30 * 24 * 3600))

    data = transaction_history_by_account(
        account_number, month_ago, today, page=1, page_size=1, transaction_pin=transaction_pin
    )

    acct = (data.get("account") or [{}])[0]
    bal_str = str(acct.get("accountBalance") or "0")
    try:
        dec = Decimal(bal_str).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return str(dec)
    except (InvalidOperation, Exception):
        return "0.00"


def fund_transfer_internal(
    *,
    amount: int,
    credit_account_name: str,
    credit_account_number: str,
    debit_account_name: str,
    debit_account_number: str,
    location: str = "NGA",
    narration: str = "",
    save_beneficiary: bool = True,
    transaction_pin: str,
) -> Dict[str, Any]:
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


def fund_transfer_outward(
    *,
    amount: int,
    credit_account_name: str,
    credit_account_number: str,
    credit_bank_code: str,
    credit_bank_name: str,
    debit_account_name: str,
    debit_account_number: str,
    location: str = "NGA",
    name_enquiry_reference: str = "",
    narration: str = "",
    save_beneficiary: bool = True,
    transaction_pin: str,
) -> Dict[str, Any]:
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
