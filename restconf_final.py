# restconf_final.py
import os
import json
import requests
from dotenv import load_dotenv
load_dotenv()
requests.packages.urllib3.disable_warnings()

ROUTER_IP = os.environ.get("ROUTER_IP")
RESTCONF_PORT = os.environ.get("RESTCONF_PORT", "443")
STUDENT_ID = os.environ.get("STUDENT_ID")

# Base URL ของ RESTCONF (IOS XE 16.9.x)
BASE = f"https://{ROUTER_IP}:{RESTCONF_PORT}/restconf"
CFG = f"{BASE}/data"
OPS = f"{BASE}/operational"

# interface ชื่อ Loopback<STUDENT_ID>
IFNAME = f"Loopback{STUDENT_ID}"

# URL config/operational ตาม YANG ietf-interfaces
api_url = f"{CFG}/ietf-interfaces:interfaces/interface={IFNAME}"
api_url_status = f"{OPS}/ietf-interfaces:interfaces-state/interface={IFNAME}"

# Headers YANG JSON
headers = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json"
}
basicauth = ("admin", "cisco")

def _ipv4_addr():
    # IP = 172.x.y.1/24 โดย x = เลขหลักร้อยของ 3 หลักท้าย, y = เลขสองหลักท้าย
    # เช่น 66070123 -> 123 => x=1, y=23
    tail3 = int(STUDENT_ID[-3:])
    x = tail3 // 100
    y = tail3 % 100
    return f"172.{x}.{y}.1", "255.255.255.0"

def create():
    # คำนวณ IP loopback จาก student ID
    ip, mask = _ipv4_addr()
    yangConfig = {
        "ietf-interfaces:interface": {
            "name": IFNAME,
            "description": f"Loopback for student {STUDENT_ID}",
            "type": "iana-if-type:softwareLoopback",
            "enabled": True,
            "ietf-ip:ipv4": {
                "address": [{"ip": ip, "netmask": mask}]
            }
        }
    }

    # ตรวจว่ามี interface อยู่แล้วหรือไม่ (ด้วย GET ก่อน)
    check = requests.get(api_url, auth=basicauth, headers=headers, verify=False)

    if check.status_code == 200:
        # มีอยู่แล้ว
        return f"Cannot create: Interface loopback {STUDENT_ID}"
    elif check.status_code == 404:
        # ไม่มี ให้สร้างใหม่ด้วย PUT
        resp = requests.put(
            api_url,
            data=json.dumps(yangConfig),
            auth=basicauth,
            headers=headers,
            verify=False
        )
        if 200 <= resp.status_code <= 299:
            return f"Interface loopback {STUDENT_ID} is created successfully"
        else:
            return f"Error (create): HTTP {resp.status_code}"
    else:
        # timeout, permission
        return f"Error checking interface: HTTP {check.status_code}"


def delete():
    resp = requests.delete(
        api_url,
        auth=basicauth,
        headers=headers,
        verify=False
    )
    if 200 <= resp.status_code <= 299:
        return f"Interface loopback {STUDENT_ID} is deleted successfully"
    elif resp.status_code == 404:
        return f"Cannot delete: Interface loopback {STUDENT_ID}"
    else:
        return f"Error (delete): HTTP {resp.status_code}"

def enable():
    yangConfig = {
        "ietf-interfaces:interface": {
            "name": IFNAME,
            "enabled": True
        }
    }
    resp = requests.patch(
        api_url,
        data=json.dumps(yangConfig),
        auth=basicauth,
        headers=headers,
        verify=False
    )
    if 200 <= resp.status_code <= 299:
        return f"Interface loopback {STUDENT_ID} is enabled successfully"
    elif resp.status_code == 404:
        return f"Cannot enable: Interface loopback {STUDENT_ID}"
    else:
        return f"Error (enable): HTTP {resp.status_code}"

def disable():
    yangConfig = {
        "ietf-interfaces:interface": {
            "name": IFNAME,
            "enabled": False
        }
    }
    resp = requests.patch(
        api_url,
        data=json.dumps(yangConfig),
        auth=basicauth,
        headers=headers,
        verify=False
    )
    if 200 <= resp.status_code <= 299:
        return f"Interface loopback {STUDENT_ID} is shutdowned successfully"
    elif resp.status_code == 404:
        return f"Cannot shutdown: Interface loopback {STUDENT_ID}"
    else:
        return f"Error (disable): HTTP {resp.status_code}"

def status():

    url = f"{CFG}/ietf-interfaces:interfaces/interface={IFNAME}"

    resp = requests.get(url, auth=basicauth, headers=headers, verify=False)

    if resp.status_code in [200]:
        try:
            data = resp.json()
            iface = data["ietf-interfaces:interface"]
            enabled = iface.get("enabled", False)
            ip_addr = iface.get("ietf-ip:ipv4", {}).get("address", [{}])[0].get("ip", "N/A")

            if enabled:
                return f"Interface loopback {STUDENT_ID} is enabled"
            else:
                return f"Interface loopback {STUDENT_ID} is disabled"
        except Exception as e:
            return f"Error reading interface: {e}"
    elif resp.status_code == 404:
        return f"No Interface loopback {STUDENT_ID}"
    else:
        return f"Error (status): HTTP {resp.status_code} {resp.text}"