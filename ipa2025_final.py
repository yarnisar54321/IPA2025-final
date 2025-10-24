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

    # แยกคำสั่งหลัง prefix "/<STUDENT_ID> "
    prefix = f"/{STUDENT_ID} "
    if not body.startswith(prefix):
        return

    cmd = body[len(prefix):].strip()
    if not cmd:
        post_text("Error: No command or unknown command")
        return

    parts = cmd.split()
    # รูปแบบตั้ง method
    if parts[0].lower() in ["restconf","netconf"]:
        current_method = parts[0].lower()
        post_text(f"Ok: {current_method.capitalize()}")
        return

    # รูปแบบตั้ง IP (เดี่ยวๆ)
    if re.match(r"^10\.0\.15\.(6[1-5])$", parts[0]):
        ip = parts[0]
        if not validate_ip(ip):
            post_text("Error: IP not allowed")
            return
        current_ip = ip
        # ถัดไปมี action อีกหรือไม่
        if len(parts) == 1:
            post_text(f"Ok: IP {current_ip}")
            return
        else:
            # มี action ต่อท้าย
            action = parts[1].lower()
            rest = parts[2:]  # อาจเป็นข้อความ MOTD
    else:
        # ไม่ได้ขึ้นต้นด้วย method หรือ IP → เป็น action เดี่ยว (ต้องมี method/IP ตั้งไว้ก่อน)
        action = parts[0].lower()
        rest = parts[1:]

    # ตรวจ method/ip ก่อนสั่งจริง
    if action in ["create","delete","enable","disable","status","motd"]:
        if action != "motd":  # งาน loopback
            if need_method(): return
            if need_ip(): return

            # ยิงไปที่ method ที่เลือก โดยส่ง IP runtime เข้า module
            if current_method == "restconf":
                res = rest_mod.dispatch(action, target_ip=current_ip)
                # แปะคำว่า using Restconf/Netconf ตามโจทย์
                if "successfully" in res or "Cannot" in res or "No Interface" in res or "Error" in res:
                    if "using Restconf" not in res and "using Netconf" not in res:
                        if "successfully" in res or "Cannot" in res:
                            res = f"{res} using Restconf"
                        elif "enabled" in res or "disabled" in res:
                            res = f"{res} (checked by Restconf)"
                post_text(res)

            elif current_method == "netconf":
                res = net_mod.dispatch(action, target_ip=current_ip)
                if "successfully" in res or "Cannot" in res or "No Interface" in res or "Error" in res:
                    if "using Restconf" not in res and "using Netconf" not in res:
                        if "successfully" in res or "Cannot" in res:
                            res = f"{res} using Netconf"
                        elif "enabled" in res or "disabled" in res:
                            res = f"{res} (checked by Netconf)"
                post_text(res)
            else:
                post_text("Error: No method specified")
            return

        # action == "motd"
        # รูปแบบ: /ID <IP> motd <ข้อความ...>  → set ด้วย Ansible
        #        /ID <IP> motd               → อ่านด้วย Netmiko/TextFSM
        if not current_ip:
            # ถ้าไม่ได้เริ่มด้วย IP ก็เช็คว่าผู้ใช้ตั้ง current_ip ไว้ก่อนแล้วหรือยัง
            if need_ip(): return

        if rest:
            banner_text = " ".join(rest)
            ok = ans.set_motd(target_ip=current_ip, banner_text=banner_text)
            post_text("Ok: success" if ok else "Error: Ansible MOTD")
        else:
            motd = nm.read_motd(ip=current_ip)
            if motd:
                post_text(motd)
            else:
                post_text("Error: No MOTD Configured")
        return

    elif action in ["gigabit_status","showrun"]:
        # ใช้ Netmiko / Ansible แบบเดิม
        if action == "gigabit_status":
            out = nm.gigabit_status(ip=current_ip) if current_ip else nm.gigabit_status()
            post_text(out)
        else:  # showrun
            res = ans.showrun()
            if res == "ok":
                # ansible_final จะส่งไฟล์กลับเองอยู่แล้วในบางเวอร์ชัน
                post_text("show running config sent.")
            else:
                post_text(res or "ok")
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
