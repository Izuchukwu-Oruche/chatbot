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
    try:
        with open("system_prompt.txt","r",encoding="utf-8") as f:
            SYSTEM_PROMPT = f.read()
    except Exception:
        s3 = boto3.client("s3")
        params = {
            "Bucket": os.environ["CFG_BUCKET"],
            "Key": os.environ["CFG_KEY"],
        }
        obj = s3.get_object(**params)
        SYSTEM_PROMPT = obj["Body"].read().decode("utf-8")

# --- AWS clients ---
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(SESSIONS_TABLE)

brt = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
