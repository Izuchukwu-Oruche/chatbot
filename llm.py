from config import brt, MODEL_ID, SYSTEM_PROMPT
import re, json

def _clean_json(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.DOTALL).strip()
    s = s.replace("\u200b","" )
    return s

def llm_parse(user_text: str, prev_intent: str = "unknown", prev_slots: dict = None) -> dict:
    prev_slots = prev_slots or {}
    user_payload = (
        f"Previous Intent: {prev_intent}\n"
        f"Known Slots (JSON): {json.dumps(prev_slots, ensure_ascii=False)}\n"
        f"User: {user_text}\n"
        f"Return STRICT JSON matching the schema."
    )
    resp = brt.converse(
        modelId=MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{"role":"user","content":[{"text": user_payload}]}],
        inferenceConfig={"maxTokens": 800, "temperature": 0.2, "topP": 0.9},
    )
    out = resp["output"]["message"]["content"][0]["text"]
    s = _clean_json(out)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # attempt commas fix
        s2 = s.replace("\n"," ")
        s2 = re.sub(r",\s*}", "}", s2)
        s2 = re.sub(r",\s*]", "]", s2)
        return json.loads(s2)

def llm_one_liner(lang: str, english_line: str) -> str:
    """Produce ONE short line in user's language (en/pcm/ig/yo/ha). No emojis/markdown."""
    sys = (
      "You write ONE short polite line in the user's language.\n"
      "No emojis, no markdown. If language code not recognized, write in simple English.\n"
      "Languages: en, pcm, ig, yo, ha."
    )
    user = f"lang={lang}\nLine: {english_line}\nReply (one line):"
    resp = brt.converse(
        modelId=MODEL_ID,
        system=[{"text": sys}],
        messages=[{"role":"user","content":[{"text": user}]}],
        inferenceConfig={"maxTokens":120,"temperature":0.3,"topP":0.9},
    )
    txt = resp["output"]["message"]["content"][0]["text"].strip()
    return txt
