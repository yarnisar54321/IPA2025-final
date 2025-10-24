# ipa2025_final.py
import os, time, json, re, requests
from dotenv import load_dotenv
from requests_toolbelt import MultipartEncoder

import restconf_final as rest_mod
import netconf_final as net_mod
import netmiko_final as nm
import ansible_final as ans

load_dotenv()

ACCESS_TOKEN = os.environ["WEBEX_ACCESS_TOKEN"]
STUDENT_ID   = os.environ["STUDENT_ID"]
ROOM_ID      = os.environ["WEBEX_ROOM_ID"]

# --- State ในโปรเซสนี้ ---
current_method = None   # "restconf" | "netconf"
current_ip     = None   # "10.0.15.61" .. "10.0.15.65"

def post_text(txt: str):
    r = requests.post(
        "https://webexapis.com/v1/messages",
        headers={"Authorization": ACCESS_TOKEN, "Content-Type":"application/json"},
        data=json.dumps({"roomId": ROOM_ID, "text": txt})
    )
    if r.status_code != 200:
        print("Post text failed:", r.status_code, r.text)

def post_file(filepath: str, caption=""):
    with open(filepath, "rb") as f:
        files = {
            "roomId": (None, ROOM_ID),
            "text": (None, caption or os.path.basename(filepath)),
            "files": (os.path.basename(filepath), f, "text/plain")
        }
        r = requests.post("https://webexapis.com/v1/messages",
                          headers={"Authorization": ACCESS_TOKEN},
                          files=files)
    if r.status_code != 200:
        post_text(f"Error sending file (HTTP {r.status_code})")

def validate_ip(ip):
    return ip in ["10.0.15.61","10.0.15.62","10.0.15.63","10.0.15.64","10.0.15.65"]

def need_method():
    if not current_method:
        post_text("Error: No method specified")
        return True
    return False

def need_ip():
    if not current_ip:
        post_text("Error: No IP specified")
        return True
    return False

def handle_command(body: str):
    global current_method, current_ip

    prefix = f"/{STUDENT_ID} "
    if not body.startswith(prefix):
        return

    # reset IP ทุกครั้งที่เริ่ม command ใหม่ของ student
    current_ip = None

    cmd = body[len(prefix):].strip()
    if not cmd:
        post_text("Error: No command or unknown command")
        return

    parts = cmd.split()

    # --- ตั้ง method ---
    if parts[0].lower() in ["restconf", "netconf"]:
        current_method = parts[0].lower()
        post_text(f"Ok: {current_method.capitalize()}")
        return

    # --- ตั้ง IP ---
    if re.match(r"^10\.0\.15\.(6[1-5])$", parts[0]):
        ip = parts[0]
        if not validate_ip(ip):
            post_text("Error: IP not allowed")
            return
        current_ip = ip
        # ถ้าใส่แค่ IP เฉยๆ
        if len(parts) == 1:
            post_text("Error: No command found.")
            return
        else:
            action = parts[1].lower()
            rest = parts[2:]
    else:
        # ถ้าไม่ใช่ IP → ถือว่าเป็น action เดี่ยว
        action = parts[0].lower()
        rest = parts[1:]

    # --- ตรวจ method / IP ก่อน ---
    if action in ["create", "delete", "enable", "disable", "status"]:
            # ถ้าไม่มี method → error ทันที
        if need_method():
            return
        # ถ้าไม่มี IP → error ทันที
        if need_ip():
            return

        # --- RESTCONF ---
        if current_method == "restconf":
            res = rest_mod.dispatch(action, target_ip=current_ip)

            # เติม suffix ตามเงื่อนไข
            if "successfully" in res:
                res = f"{res} using Restconf"
            elif "Cannot" in res:
                res = res
            elif any(word in res for word in ["enabled", "disabled", "No Interface"]):
                res = f"{res} (checked by Restconf)"
            post_text(res)

        # --- NETCONF ---
        elif current_method == "netconf":
            res = net_mod.dispatch(action, target_ip=current_ip)

            if "successfully" in res:
                res = f"{res} using Netconf"
            elif "Cannot" in res:
                res = res
            elif any(word in res for word in ["enabled", "disabled", "No Interface"]):
                res = f"{res} (checked by Netconf)"
            post_text(res)
        return

    else:
        post_text("Error: No command found.")

def main_loop():
    while True:
        time.sleep(1)
        r = requests.get(
            "https://webexapis.com/v1/messages",
            params={"roomId": ROOM_ID, "max": 1},
            headers={"Authorization": ACCESS_TOKEN},
        )
        if r.status_code != 200:
            print("Webex API error:", r.status_code, r.text)
            continue
        items = r.json().get("items", [])
        if not items:
            continue
        msg = items[0].get("text","")
        if not msg:
            continue
        print("Received:", msg)
        handle_command(msg)

if __name__ == "__main__":
    main_loop()
