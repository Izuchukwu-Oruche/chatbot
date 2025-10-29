from config import GRAPH_API_VERSION, PHONE_NUMBER_ID, WHATSAPP_TOKEN
import urllib.request, json

def wa_ok(body="OK", status=200):
    return {"statusCode": status, "headers": {"Content-Type":"text/plain"}, "body":body}

def wa_send_text(to: str, body: str):
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    payload = {"messaging_product":"whatsapp","to":to,"type":"text","text":{"body": body[:4000]}}
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST",
                                 headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}","Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        _ = r.read()

def extract_messages(event_body: dict):
    msgs = []
    for entry in event_body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for m in value.get("messages", []) or []:
                if m.get("type") == "text" and "from" in m:
                    msgs.append({"from": m["from"], "text": m["text"]["body"].strip()})
    return msgs
