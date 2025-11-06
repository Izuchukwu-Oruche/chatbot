"""
Bedrock LLM utilities:
  - `llm_parse`: structured parse for intent/slots/action/lang
  - `llm_one_liner`: short professional line in requested language

These helpers are intentionally thin; they keep the calling code simple.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from config import brt, MODEL_ID, SYSTEM_PROMPT


def _clean_json(s: str) -> str:
    """
    Strip code fences / zero-width chars and return a best-effort JSON string.
    """
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.DOTALL).strip()
    s = s.replace("\u200b", "")
    return s


def llm_parse(
    user_text: str,
    prev_intent: str = "unknown",
    prev_slots: Optional[Dict[str, Any]] = None,
    preferred_lang: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ask the model to return STRICT JSON for NLU parsing.
    """
    prev_slots = prev_slots or {}
    lang_line = f"Preferred Reply Language: {preferred_lang or 'auto'}\n"
    user_payload = (
        f"Previous Intent: {prev_intent}\n"
        f"Known Slots (JSON): {json.dumps(prev_slots, ensure_ascii=False)}\n"
        + lang_line
        + f"User: {user_text}\n"
        f"Return STRICT JSON matching the schema."
    )

    resp = brt.converse(
        modelId=MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": user_payload}]}],
        inferenceConfig={"maxTokens": 800, "temperature": 0.2, "topP": 0.9},
    )
    out = resp["output"]["message"]["content"][0]["text"]
    s = _clean_json(out)

    # Tolerate trailing commas / line breaks
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        s2 = s.replace("\n", " ")
        s2 = re.sub(r",\s*}", "}", s2)
        s2 = re.sub(r",\s*]", "]", s2)
        return json.loads(s2)


def llm_one_liner(lang: str, english_line: str) -> str:
    """
    Produce ONE short professional line in user's language (en/pcm/ig/yo/ha).

    Rules:
      - Neutral, professional tone. No jokes, no commentary, no emojis.
      - Preserve currency/number formatting exactly.
      - No English or code-mix for pcm/ig/yo/ha.
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
        messages=[{"role": "user", "content": [{"text": u}]}],
        inferenceConfig={"maxTokens": 120, "temperature": 0.2, "topP": 0.9},
    )
    txt = resp["output"]["message"]["content"][0]["text"].strip()
    return txt
