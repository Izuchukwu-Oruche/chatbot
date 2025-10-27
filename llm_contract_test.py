import os, json, decimal, re
import boto3

# -------- Config --------
REGION = os.getenv("BEDROCK_REGION", "us-east-1")
# Example Anthropic Sonnet ID on Bedrock; make this configurable:
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-haiku-20241022-v1:0")


SYSTEM_PROMPT = open("system_prompt.txt", "r", encoding="utf-8").read()

session = boto3.Session(profile_name="Izu", region_name="us-east-1")
brt = session.client("bedrock-runtime")

# brt = boto3.client("bedrock-runtime")

def call_bedrock(messages):
    """messages: list of {'role': 'user'|'assistant'|'system', 'content': [{'type':'text','text':...}]}"""
    resp = brt.converse(
        modelId=MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=messages,
        inferenceConfig={
            "maxTokens": 800,
            "temperature": 0.2,
            "topP": 0.9,
        },
    )
    out = resp["output"]["message"]["content"][0]["text"]
    # Hard-guard: strip code fences if any (model shouldn't produce them, but just in case)
    out = re.sub(r"^```(?:json)?|```$", "", out.strip())
    return out

def safe_json_loads(s):
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # Try common fixes
        s = s.strip()
        s = s.replace("\n", " ")
        s = re.sub(r",\s*}", "}", s)
        s = re.sub(r",\s*]", "]", s)
        return json.loads(s)

def test_one(utterance):
    msg = [{"role":"user","content":[{"text": utterance}]}]
    raw = call_bedrock(msg)
    print("\nRAW:", raw)
    data = safe_json_loads(raw)
    print("PARSED:", json.dumps(data, indent=2, ensure_ascii=False))
    return data

if __name__ == "__main__":
    tests = [
        "Mo fe iranlowo. Ṣe o le ṣe iranlọwọ fun mi?"
    ]
    for t in tests:
        print("\n=== INPUT:", t)
        _ = test_one(t)
