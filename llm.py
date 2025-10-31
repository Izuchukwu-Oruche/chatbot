from config import brt, MODEL_ID, SYSTEM_PROMPT
import re, json

def _clean_json(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.DOTALL).strip()
    s = s.replace("\u200b","" )
    return s

def llm_parse(user_text: str, prev_intent: str = "unknown", prev_slots: dict = None, preferred_lang: str = None) -> dict:
    prev_slots = prev_slots or {}
    lang_line = f"Preferred Reply Language: {preferred_lang or 'auto'}\n"
    user_payload = (
        f"Previous Intent: {prev_intent}\n"
        f"Known Slots (JSON): {json.dumps(prev_slots, ensure_ascii=False)}\n"
        + lang_line +
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
        s2 = s.replace("\n"," ")
        s2 = re.sub(r",\s*}", "}", s2)
        s2 = re.sub(r",\s*]", "]", s2)
        return json.loads(s2)

def llm_one_liner(lang: str, english_line: str) -> str:
    """
    Produce ONE short professional line in user's language (en/pcm/ig/yo/ha).
    Rules:
      - Neutral, professional tone. No jokes, no commentary, no emojis.
      - Preserve numbers and currency exactly (e.g., "NGN 151,170.50" must stay exactly that).
      - Do NOT add opinions like "no be small money", "high well", etc.
      - If lang is pcm/ig/yo/ha, DO NOT output English or code-mix.
      - If the input already matches the target language, return a minimal natural version.
      - Preferred templates (examples):
          pcm: "Balance na NGN 151,170.50."
          ig:  "Ego fọdụrụ n’akaụntụ gị bụ NGN 151,170.50."
          yo:  "Iwontunwonsi àkàǹtì rẹ jẹ́ NGN 151,170.50."
          ha:  "Adadin kuɗinka shi ne NGN 151,170.50."
      - For transfer success: use equivalents of "Transfer successful. Reference XYZ."
      - For transfer failure: equivalents of "Transfer failed: REASON."
    """
    sys = (
      "Translate or rewrite the given line into the exact target language indicated by 'lang'.\n"
      "STRICT RULES:\n"
      "1) Return ONE short professional sentence; no emojis, no extra words.\n"
      "2) If the line contains a money amount like 'NGN 123,456.78', PRESERVE the currency and digits exactly.\n"
      "3) Do NOT add opinions, jokes, or commentary.\n"
      "4) If lang is pcm/ig/yo/ha, do NOT output English or code-mix.\n"
      "5) Use the neutral templates for that language.\n"
      "6) Output only the sentence."
    )
    u = f"lang={lang}\nLine: {english_line}\nReply (one sentence only):"
    resp = brt.converse(
        modelId=MODEL_ID,
        system=[{"text": sys}],
        messages=[{"role":"user","content":[{"text": u}]}],
        inferenceConfig={"maxTokens":120,"temperature":0.2,"topP":0.9},
    )
    txt = resp["output"]["message"]["content"][0]["text"].strip()
    return txt
