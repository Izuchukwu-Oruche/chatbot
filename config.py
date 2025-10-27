import os
import boto3

GRAPH_API_VERSION = os.environ["GRAPH_API_VERSION"]
PHONE_NUMBER_ID   = os.environ["PHONE_NUMBER_ID"]
WHATSAPP_TOKEN    = os.environ["WHATSAPP_TOKEN"]
VERIFY_TOKEN      = os.environ["VERIFY_TOKEN"]
BEDROCK_REGION    = os.getenv("BEDROCK_REGION","us-east-1")
MODEL_ID          = os.getenv("BEDROCK_MODEL_ID","us.anthropic.claude-3-5-haiku-20241022-v1:0")
# SYSTEM_PROMPT     = os.environ["SYSTEM_PROMPT"]


s3 = boto3.client("s3")
CFG = None

if CFG is None:
    params = {
        "Bucket": os.environ["CFG_BUCKET"],
        "Key": os.environ["CFG_KEY"],
    }
    obj = s3.get_object(**params)
    body = obj["Body"].read().decode("utf-8")
    

brt = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)