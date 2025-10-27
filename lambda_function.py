import json
from config import VERIFY_TOKEN
from whatsapp_helpers import wa_ok, extract_messages
from main_logic import handle_text




def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod","GET")

    if method == "GET":
        params = event.get("queryStringParameters") or {}
        if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
            return wa_ok(params.get("hub.challenge",""), 200)
        return wa_ok("forbidden", 403)

    if method == "POST":
        try:
            body = json.loads(event.get("body") or "{}")
        except Exception:
            return wa_ok("bad request", 400)

        if body.get("object") != "whatsapp_business_account":
            return wa_ok("ignored", 200)

        for msg in extract_messages(body):
            try:
                handle_text(msg["from"], msg["text"])
            except Exception as e:
                print("ERR handle_text:", e)
        return wa_ok("ok", 200)

    return wa_ok("method not allowed", 405)