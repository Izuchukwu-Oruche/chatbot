from config import brt, MODEL_ID, SYSTEM_PROMPT
import re, json

def llm_parse(user_text: str) -> dict:
    resp = brt.converse(
        modelId=MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{"role":"user","content":[{"text": user_text}]}],
        inferenceConfig={"maxTokens": 800, "temperature": 0.2, "topP": 0.9},
    )
    content = resp.get("output",{}).get("message",{}).get("content",[])
    if not content or "text" not in content[0]:
        raise RuntimeError(f"LLM response missing text: {resp}")
    out = content[0]["text"].strip()
    out = re.sub(r"^```(?:json)?\s*|\s*```$", "", out, flags=re.DOTALL).strip()
    out = out.replace("\u200b","")
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        s = out.replace("\n"," ")
        s = re.sub(r",\s*}", "}", s); s = re.sub(r",\s*]", "]", s)
        return json.loads(s)

def llm_confirm(lang: str, canonical_en: str, outcome_en: str) -> str:
    """Use a tiny prompt to produce a 1-line confirmation in user's language."""
    sys = (
      "You write ONE short polite line in the user's language.\n"
      "No emojis, no markdown. If language code not recognized, write in simple English.\n"
      "Languages: en, pcm, ig, yo, ha."
    )
    user = f"lang={lang}\nRequest: {canonical_en}\nOutcome: {outcome_en}\nReply (one line):"
    resp = brt.converse(
        modelId=MODEL_ID,
        system=[{"text": sys}],
        messages=[{"role":"user","content":[{"text": user}]}],
        inferenceConfig={"maxTokens":120,"temperature":0.3,"topP":0.9},
    )
    txt = resp["output"]["message"]["content"][0]["text"].strip()
    return txt
