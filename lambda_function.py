import json
from config import VERIFY_TOKEN
from http_utils import ok, extract_messages
from bedrock_call import call_bedrock
from whatsapp import wa_send_text


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod","GET")

    # --- Webhook verification (GET) ---
    if method == "GET":
        params = event.get("queryStringParameters") or {}
        mode  = params.get("hub.mode")
        token = params.get("hub.verify_token")
        chal  = params.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN and chal:
            return ok(chal, 200)
        return ok("forbidden", 403)

    # --- Message ingest (POST) ---
    if method == "POST":
        try:
            body = json.loads(event.get("body") or "{}")
        except Exception:
            return ok("bad request", 400)

        # Ignore non-message deliveries
        if body.get("object") != "whatsapp_business_account":
            return ok("ignored", 200)

        for msg in extract_messages(body):
            from_id = msg["from"]
            text    = msg["text"].strip()

            # Run NLU on Bedrock
            try:
                parsed = call_bedrock(text)
                lang = parsed.get("lang",{}).get("detected","?")
                intent = parsed.get("intent","unknown")
                missing = parsed.get("missing_slots",[])
                canonical = parsed.get("canonical_en","")
                # Simple echo reply for Step 2:
                reply = (
                    f"lang={lang} | intent={intent}\n"
                    f"missing={missing if missing else '[]'}\n"
                    f"{'→ ' + canonical if canonical else ''}"
                )
            except Exception as e:
                reply = "Sorry, I couldn't parse that. Please try again."

            # Send reply to WhatsApp
            try:
                wa_send_text(from_id, reply)
            except Exception as e:
                # Log but don't fail the webhook 200
                print("WA SEND ERROR:", e)

        return ok("ok", 200)

    return ok("method not allowed", 405)
