from config import brt
from config import MODEL_ID, body
import re, json


def call_bedrock(user_text: str) -> dict:
    resp = brt.converse(
        modelId=MODEL_ID,
        system=[{"text": body}],
        messages=[{"role":"user","content":[{"text": user_text}]}],
        inferenceConfig={"maxTokens":800,"temperature":0.2,"topP":0.9}
    )
    out = resp["output"]["message"]["content"][0]["text"].strip()
    # Defensive clean-up in case the model adds fences:
    out = re.sub(r"^```(?:json)?\s*|\s*```$", "", out, flags=re.DOTALL).strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        # Try minor repairs then raise
        s = out.replace("\n"," ")
        s = re.sub(r",\s*}", "}", s); s = re.sub(r",\s*]", "]", s)
        return json.loads(s)
