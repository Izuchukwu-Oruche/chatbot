import json

def ok(body="OK", status=200):
    return {"statusCode": status,
            "headers": {"Content-Type":"text/plain"},
            "body": body}

def json(body, status=200):
    return {"statusCode": status,
            "headers": {"Content-Type":"application/json"},
            "body": json.dumps(body)}

def extract_messages(event_body: dict):
    # WhatsApp Cloud API delivers messages under entry[].changes[].value.messages[]
    msgs = []
    for entry in event_body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = {c.get("wa_id"): c for c in value.get("contacts", [])}
            for m in value.get("messages", []) or []:
                if m.get("type") == "text" and "from" in m:
                    msgs.append({
                        "from": m["from"],
                        "text": m["text"]["body"],
                        "profile": contacts.get(m["from"], {})
                    })
    return msgs