import os
import boto3

# --- WhatsApp / Graph ---
GRAPH_API_VERSION = os.environ.get("GRAPH_API_VERSION", "v20.0")
PHONE_NUMBER_ID   = os.environ.get("PHONE_NUMBER_ID", "")
WHATSAPP_TOKEN    = os.environ.get("WHATSAPP_TOKEN", "")
VERIFY_TOKEN      = os.environ.get("VERIFY_TOKEN", "")

# --- Bedrock ---
BEDROCK_REGION    = os.getenv("BEDROCK_REGION","us-east-1")
MODEL_ID          = os.getenv("BEDROCK_MODEL_ID","us.anthropic.claude-3-5-haiku-20241022-v1:0")

# --- Sessions (DynamoDB) ---
SESSIONS_TABLE    = os.environ.get("SESSIONS_TABLE", "wa-bot-sessions")

# --- Finlake headers ---
ACCOUNT_ID        = os.environ.get("ACCOUNT_ID","")        # X-Account-Id
FLK_STAGE         = os.environ.get("FLK_STAGE","dev")       # X-Flk-Stage (e.g., dev, prod)

# --- Phone credentials used inside Finlake credentials payload ---
PHONE_COUNTRY_CODE = os.environ.get("PHONE_COUNTRY_CODE","234")
PHONE_NUMBER       = os.environ.get("PHONE_NUMBER","")

# --- Optional legacy config ---
BANK_API_BASE   = os.getenv("BANK_API_BASE","")
BANK_API_TOKEN  = os.getenv("BANK_API_TOKEN","")

# --- System Prompt loading order: ENV -> local file -> S3 ---
SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT")
if not SYSTEM_PROMPT:
    # Try local file first
    try:
        with open("system_prompt.txt","r",encoding="utf-8") as f:
            SYSTEM_PROMPT = f.read()
    except Exception:
        # Fallback to S3 if configured, else last-resort default
        try:
            bucket = os.getenv("CFG_BUCKET")
            key = os.getenv("CFG_KEY")
            if bucket and key:
                s3 = boto3.client("s3")
                obj = s3.get_object(Bucket=bucket, Key=key)
                SYSTEM_PROMPT = obj["Body"].read().decode("utf-8")
            else:
                SYSTEM_PROMPT = SYSTEM_PROMPT or "You are a multilingual Nigerian banking NLU. Output only strict JSON."
        except Exception:
            SYSTEM_PROMPT = SYSTEM_PROMPT or "You are a multilingual Nigerian banking NLU. Output only strict JSON."


# --- AWS clients ---
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(SESSIONS_TABLE)

brt = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
