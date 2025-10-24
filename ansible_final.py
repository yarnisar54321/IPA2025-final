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
        cmd = ["ansible-playbook", "-i", "hosts", "playbook.yaml"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + "\n" + result.stderr
        print(output)

        if "failed=0" not in output.lower():
            return "Error: Ansible"

        filename = f"show_run_{STUDENT_ID}_{ROUTER_NAME}.txt"
        if not os.path.exists(filename):
            return f"Error: File {filename} not found"

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
            return "Ok: showrun completed"
        else:
            return f"Error sending file to Webex (HTTP {resp.status_code})"

    except Exception as e:
        return f"Error (showrun): {str(e)}"


def set_motd(target_ip, banner_text):
    """
    ใช้ ansible ตั้งค่า MOTD banner บน router
    """
    try:
        with open("hosts", "w") as hosts:
            hosts.write(f"router1 ansible_host={target_ip} ansible_user=admin ansible_password=cisco ansible_network_os=ios ansible_connection=network_cli ansible_command_timeout=180 ansible_connect_timeout=60")
    
        # เรียก playbook.yaml แล้วส่งตัวแปร target_ip และ motd_text ไป
        cmd = [
            "ansible-playbook",
            "motd.yaml",
            "-i", f"hosts",
            "-e", f"motd_text='{banner_text}'"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("MOTD set successfully!")
            return True
        else:
            print("Ansible Error:", result.stderr)
            return False

    except Exception as e:
        print("Error running Ansible:", e)
        return False
