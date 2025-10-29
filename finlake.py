import time, base64
import requests
from typing import TypedDict, List, Optional

#CREDENTIALS
PHONE_COUNTRY_CODE = "234"
PHONE_NUMBER = "9"
TRANSACTION_PIN = ""
ACCOUNT_ID = ""
FLK_STAGE = ""


#baseurl
BASE_URL = "https://api-dev.finlake.tech/mobility"

# Response Models
class BankInfo(TypedDict):
    bankCategory: int
    bankCode: str
    bankLogoUrl: str
    bankName: str
    bankShortName: str

class BankListResponse(TypedDict):
    data: List[BankInfo]
    responseCode: str
    responseMessage: str

class ApiResponse(TypedDict):
    data: Optional[dict]
    responseCode: str
    responseMessage: str

class AccountInfo(TypedDict):
    accountBalance: str
    accountBranchCode: str
    accountCategory: str
    accountChecker: str
    accountClass: str
    accountCreatedAt: str
    accountCurrencyCode: str
    accountCustomerId: str
    accountDailyCredit: str
    accountDailyDebit: str
    accountEndDate: str
    accountGlLevel2Code: str
    accountId: int
    accountInterest: str
    accountInterestRate: str
    accountLienAmount: str
    accountMaker: str
    accountMonthlyCredit: str
    accountMonthlyDebit: str
    accountName: str
    accountNumber: str
    accountParent: str
    accountPenalty: str
    accountPnd: str
    accountStatus: str
    accountSync: str
    accountSyncAttempt: int
    accountSyncFailureReason: str
    accountTotalCredit: str
    accountTotalDebit: str
    accountUpdatedAt: str

class TransactionInfo(TypedDict):
    accountName: str
    accountNumber: str
    amount: str
    contractReference: str
    counterPartyAccountName: str
    counterPartyAccountNumber: str
    counterPartyBank: str
    counterPartyBankCode: str
    counterPartyChannel: str
    counterPartyService: str
    drCr: str
    eventDate: str
    id: str
    narration: str
    paymentReference: str
    responseCode: str
    responseMessage: str
    transactionDate: str
    transactionType: str
    trnAmount: str

class CustomerByAccountNumberResponse(TypedDict):
    account: List[AccountInfo]
    data: List[TransactionInfo]
    responseCode: str
    responseMessage: str

class NameEnquiryData(TypedDict):
    accountCurrencyCode: str
    accountName: str
    accountNumber: str

class InternalNameEnquiryResponse(TypedDict):
    data: NameEnquiryData
    responseCode: str
    responseMessage: str

class StatementTransactionItem(TypedDict):
    account: str
    accountName: str
    amount: str
    contractRef: str
    counterparty: str
    counterpartyBank: str
    counterpartyBankCode: str
    counterpartyChannel: str
    counterpartyService: str
    drCr: str
    eventdate: str
    id: str
    logoUrl: str
    narration: str
    paymentRef: str
    runningBalance: int
    runningTotal: str
    trnType: str
    txnDate: str

class RequestCustomerStatementResponse(TypedDict):
    accountName: str
    accountNumber: str
    accountType: str
    address: str
    bankname: str
    closingBalance: str
    color: str
    colorfade: str
    email: str
    endDate: str
    logo: str
    openingBalance: str
    responseCode: str
    responseMessage: str
    sendMail: bool
    startDate: str
    supportemail: str
    supportphone: str
    totalCredit: str
    totalDebit: str
    transactionList: List[StatementTransactionItem]
    transactionListString: str

class FundTransferInternalResponse(TypedDict):
    cbaReference: str
    creditAccountBankCode: str
    creditAccountBankName: str
    creditAccountNumber: str
    debitAccountNumber: str
    reference: str
    requestTime: str
    responseCode: str
    responseMessage: str
    responseTime: str
    totalFee: str
    totalVat: str
    trnAmount: str
    trnNarration: str

class FundTransferOutwardResponse(TypedDict):
    amount: int
    beneficiaryAccountName: str
    beneficiaryAccountNumber: str
    beneficiaryBankVerificationNumber: str
    beneficiaryKYCLevel: str
    cbaReference: str
    channelCode: int
    destinationInstitutionCode: str
    nameEnquiryRef: str
    narration: str
    originatorAccountName: str
    originatorAccountNumber: str
    originatorBankVerificationNumber: str
    originatorKYCLevel: str
    paymentReference: str
    responseCode: str
    responseMessage: str
    sessionID: str
    totalFee: str
    totalVat: str
    transactionId: str
    transactionLocation: str

class GetUserInfoResponse(TypedDict):
    accountId: int
    accounts: List[AccountInfo]
    address: str
    deviceToken: str
    privileges: List[str]
    responseCode: str
    responseMessage: str
    token: str
    userCountryCode: str
    userDob: str
    userEmail: str
    userFirstName: str
    userFullName: str
    userGender: str
    userId: str
    userInviteCode: str
    userLastName: str
    userPhoneNumber: str
    userReferralCode: str
    userRewardBalance: int
    userRoleId: int
    userStatus: str
    userTierId: int

def generate_credentials(phone_country_code: str, phone_number: str, transaction_pin: str) -> dict:
    signature = f"{time.time()}:chatbot"
    return {
        "phoneCountryCode": phone_country_code,
        "phoneNumber": phone_number,
        "requestSignature": base64.b64encode(signature.encode()).decode(),
        "transactionPin": transaction_pin
    }

def handle_response(response: requests.Response, response_model: Optional[type] = None) -> dict:
    if response.status_code == 200:
        data = response.json()
        # Validate success: status code 200 and responseCode "00"
        if isinstance(data, dict) and data.get("responseCode") != "00":
            raise Exception(
                f"API request failed: responseCode={data.get('responseCode')}, "
                f"responseMessage={data.get('responseMessage', 'Unknown error')}"
            )
        return data
    else:
        raise Exception(f"HTTP request failed: {response.status_code} {response.text}")

def get_bank_list() -> BankListResponse:
    url = f"{BASE_URL}/public/read/cts-bank"
    payload = generate_credentials(PHONE_COUNTRY_CODE, PHONE_NUMBER, TRANSACTION_PIN)
    headers = {
        "Content-Type": "application/json",
        "X-Account-Id": ACCOUNT_ID,
        "X-Flk-Stage": FLK_STAGE
    }
    response = requests.post(url, json=payload, headers=headers)

    return handle_response(response)

def fund_transfer_internal(
    amount: int, 
    credit_account_name: str, 
    credit_account_number: str, 
    debit_account_name: str, 
    debit_account_number: str, 
    location: str, 
    narration: str, 
    save_beneficiary: bool, 
    transaction_pin: str
) -> FundTransferInternalResponse:
    url = f"{BASE_URL}/public/create/cts-internal-fund-transfer"
    payload = {
        "amount": str(amount),
        "creditAccountName": credit_account_name,
        "creditAccountNumber": credit_account_number,
        "debitAccountName": debit_account_name,
        "debitAccountNumber": debit_account_number,
        "location": location,
        "narration": narration,
        "saveBeneficiary": save_beneficiary,
        "transactionPin": transaction_pin,
        "credentials": generate_credentials(PHONE_COUNTRY_CODE, PHONE_NUMBER, TRANSACTION_PIN)
    }
    headers = {
        "Content-Type": "application/json",
        "X-Account-Id": ACCOUNT_ID,
        "X-Flk-Stage": FLK_STAGE
    }
    response = requests.post(url, json=payload, headers=headers)

    return handle_response(response)

def fund_transfer_outward(
    amount: int,
    credit_account_name: str,
    credit_account_number: str,
    credit_bank_code: str,
    credit_bank_name: str,
    debit_account_name: str,
    debit_account_number: str,
    location: str,
    name_enquiry_reference: str,
    narration: str,
    save_beneficiary: bool,
    transaction_pin: str
) -> FundTransferOutwardResponse:
    url = f"{BASE_URL}/public/create/cts-outward-fund-transfer"
    payload = {
        "amount": str(amount),
        "credentials": generate_credentials(PHONE_COUNTRY_CODE, PHONE_NUMBER, TRANSACTION_PIN),
        "creditAccountName": credit_account_name,
        "creditAccountNumber": credit_account_number,
        "creditBankCode": credit_bank_code,
        "creditBankName": credit_bank_name,
        "debitAccountName": debit_account_name,
        "debitAccountNumber": debit_account_number,
        "location": location,
        "nameEnquiryReference": name_enquiry_reference,
        "narration": narration,
        "saveBeneficiary": save_beneficiary,
        "transactionPin": transaction_pin
    }
    headers = {
        "Content-Type": "application/json",
        "X-Account-Id": ACCOUNT_ID,
        "X-Flk-Stage": FLK_STAGE
    }
    response = requests.post(url, json=payload, headers=headers)

    return handle_response(response)

def get_customer_by_account_number(
    account_number: str,
    start_date: str,
    end_date: str,
    page: int,
    page_size: int,
    transaction_pin: str
) -> CustomerByAccountNumberResponse:
    url = f"{BASE_URL}/public/read/cts-by-account-number"
    payload = {
        "accountNumber": account_number,
        "credentials": generate_credentials(PHONE_COUNTRY_CODE, PHONE_NUMBER, transaction_pin),
        "startDate": start_date,
        "endDate": end_date,
        "page": page,
        "pageSize": page_size
    }
    headers = {
        "Content-Type": "application/json",
        "X-Account-Id": ACCOUNT_ID,
        "X-Flk-Stage": FLK_STAGE
    }
    response = requests.post(url, json=payload, headers=headers)

    return handle_response(response)

def internal_name_enquiry(
    account_number: str,
    transaction_pin: str
) -> InternalNameEnquiryResponse:
    url = f"{BASE_URL}/public/read/cts-internal-name-enquiry"
    payload = {
        "accountNumber": account_number,
        "credentials": generate_credentials(PHONE_COUNTRY_CODE, PHONE_NUMBER, transaction_pin)
    }
    headers = {
        "Content-Type": "application/json",
        "X-Account-Id": ACCOUNT_ID,
        "X-Flk-Stage": FLK_STAGE
    }
    response = requests.post(url, json=payload, headers=headers)

    return handle_response(response)

def get_user_info(transaction_pin: str) -> GetUserInfoResponse:
    url = f"{BASE_URL}/public/read/cts-user-info"
    payload = generate_credentials(PHONE_COUNTRY_CODE, PHONE_NUMBER, transaction_pin)
    headers = {
        "Content-Type": "application/json",
        "X-Account-Id": ACCOUNT_ID,
        "X-Flk-Stage": FLK_STAGE
    }
    response = requests.post(url, json=payload, headers=headers)

    return handle_response(response)

def request_customer_statement(
    account_number: str,
    email: str,
    start_date: str,
    end_date: str,
    transaction_pin: str
) -> RequestCustomerStatementResponse:
    url = f"{BASE_URL}/public/read/cts-request-statement"
    payload = {
        "accountNumber": account_number,
        "credentials": generate_credentials(PHONE_COUNTRY_CODE, PHONE_NUMBER, transaction_pin),
        "email": email,
        "startDate": start_date,
        "endDate": end_date
    }
    headers = {
        "Content-Type": "application/json",
        "X-Account-Id": ACCOUNT_ID,
        "X-Flk-Stage": FLK_STAGE
    }
    response = requests.post(url, json=payload, headers=headers)

    return handle_response(response)