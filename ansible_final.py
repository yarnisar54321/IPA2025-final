import os
import subprocess
import requests
from dotenv import load_dotenv, find_dotenv

# โหลดค่าจากไฟล์ .env

load_dotenv(find_dotenv())


WEBEX_ACCESS_TOKEN = os.getenv("WEBEX_ACCESS_TOKEN")
WEBEX_ROOM_ID = os.getenv("WEBEX_ROOM_ID")
STUDENT_ID = os.getenv("STUDENT_ID")
ROUTER_NAME = "CSR1KV"   # เปลี่ยนตาม Pod ของคุณ (Pod2-1, Pod3-1, ...)

def showrun():
    """
    เรียก ansible-playbook เพื่อ backup running-config
    แล้วส่งไฟล์ .txt กลับไปที่ Webex Room
    """
    try:
        # 1 รัน ansible-playbook
        cmd = ["ansible-playbook", "-i", "hosts", "playbook.yaml"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + "\n" + result.stderr
        print(output)

        # 2 ตรวจว่าทำงานสำเร็จหรือไม่
        if "failed=0" not in output.lower():
            return "Error: Ansible"

        # 3 ตรวจว่าไฟล์ถูกสร้างจริง
        filename = f"show_run_{STUDENT_ID}_{ROUTER_NAME}.txt"
        if not os.path.exists(filename):
            return f"Error: File {filename} not found"

        # 4 ส่งไฟล์กลับไปยัง Webex Room
        print(f"Sending {filename} to Webex room...")

        url = "https://webexapis.com/v1/messages"
        headers = {"Authorization": WEBEX_ACCESS_TOKEN} 
        with open(filename, "rb") as f:
            files = {
                "roomId": (None, WEBEX_ROOM_ID),
                "text": (None, f"show running config"),
                "files": (filename, f, "text/plain")
            }
            resp = requests.post(url, headers=headers, files=files)

        if resp.status_code == 200:
            return 
        else:
            return f"Error sending file to Webex (HTTP {resp.status_code})"

    except Exception as e:
        return f"Error (showrun): {str(e)}"


