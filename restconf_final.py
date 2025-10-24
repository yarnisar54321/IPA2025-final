# restconf_final.py
import os, json, requests
from dotenv import load_dotenv
load_dotenv()
requests.packages.urllib3.disable_warnings()

RESTCONF_PORT = os.environ.get("RESTCONF_PORT", "443")
STUDENT_ID = os.environ.get("STUDENT_ID")
IFNAME = f"Loopback{STUDENT_ID}"
AUTH = ("admin","cisco")
HEADERS = {
    "Accept":"application/yang-data+json",
    "Content-Type":"application/yang-data+json"
}

def _ipv4_addr():
    tail3 = int(STUDENT_ID[-3:])
    x = tail3 // 100
    y = tail3 % 100
    return f"172.{x}.{y}.1", "255.255.255.0"

def _urls(ip):
    base = f"https://{ip}:{RESTCONF_PORT}/restconf"
    cfg  = f"{base}/data"
    ops  = f"{base}/operational"
    api_url = f"{cfg}/ietf-interfaces:interfaces/interface={IFNAME}"
    api_status = f"{ops}/ietf-interfaces:interfaces-state/interface={IFNAME}"
    return api_url, api_status, cfg

def create(ip):
    api_url, _, _ = _urls(ip)
    ipaddr, mask = _ipv4_addr()
    yang = {
        "ietf-interfaces:interface": {
            "name": IFNAME,
            "description": f"Loopback for student {STUDENT_ID}",
            "type": "iana-if-type:softwareLoopback",
            "enabled": True,
            "ietf-ip:ipv4": {"address": [{"ip": ipaddr, "netmask": mask}]}
        }
    }

    # ตรวจสอบก่อนว่ามีอยู่แล้วหรือไม่
    check = requests.get(api_url, auth=AUTH, headers=HEADERS, verify=False)

    if check.status_code == 200:
        # มี interface เดิมอยู่แล้ว → ห้ามสร้างซ้ำ
        return f"Cannot create: Interface loopback {STUDENT_ID}"

    elif check.status_code == 404:
        # ไม่พบ interface → สร้างใหม่
        resp = requests.put(api_url, data=json.dumps(yang), auth=AUTH, headers=HEADERS, verify=False)
        if 200 <= resp.status_code <= 299:
            return f"Interface loopback {STUDENT_ID} is created successfully"
        else:
            return f"Error (create): HTTP {resp.status_code}"

    else:
        # กรณีอื่น ๆ (เช่น 401 / 500)
        return f"Error checking interface: HTTP {check.status_code}"


def delete(ip):
    api_url, _, _ = _urls(ip)
    # ตรวจว่ามี interface อยู่จริงไหมก่อน
    check = requests.get(api_url, auth=AUTH, headers=HEADERS, verify=False)

    if check.status_code == 404:
        # ถ้าไม่มีอยู่ → ลบไม่ได้
        return f"Cannot delete: Interface loopback {STUDENT_ID}"

    elif check.status_code == 200:
        # ถ้ามีอยู่ → ลบได้
        resp = requests.delete(api_url, auth=AUTH, headers=HEADERS, verify=False)
        if 200 <= resp.status_code <= 299:
            return f"Interface loopback {STUDENT_ID} is deleted successfully"
        else:
            return f"Error (delete): HTTP {resp.status_code}"

    else:
        return f"Error checking interface: HTTP {check.status_code}"


def enable(ip):
    api_url, _, _ = _urls(ip)
    yang = {"ietf-interfaces:interface":{"name":IFNAME,"enabled":True}}
    resp = requests.patch(api_url, data=json.dumps(yang), auth=AUTH, headers=HEADERS, verify=False)
    if 200 <= resp.status_code <= 299:
        return f"Interface loopback {STUDENT_ID} is enabled successfully"
    elif resp.status_code == 404:
        return f"Cannot enable: Interface loopback {STUDENT_ID}"
    return f"Error (enable): HTTP {resp.status_code}"

def disable(ip):
    api_url, _, _ = _urls(ip)
    yang = {"ietf-interfaces:interface":{"name":IFNAME,"enabled":False}}
    resp = requests.patch(api_url, data=json.dumps(yang), auth=AUTH, headers=HEADERS, verify=False)
    if 200 <= resp.status_code <= 299:
        return f"Interface loopback {STUDENT_ID} is shutdowned successfully"
    elif resp.status_code == 404:
        return f"Cannot shutdown: Interface loopback {STUDENT_ID}"
    return f"Error (disable): HTTP {resp.status_code}"

def status(ip):
    api_url, api_status, _ = _urls(ip)

    # ขั้นแรก: ตรวจจาก config ก่อน
    cfg = requests.get(api_url, auth=AUTH, headers=HEADERS, verify=False)
    if cfg.status_code == 200:
        try:
            iface = cfg.json()["ietf-interfaces:interface"]
            enabled = iface.get("enabled", False)
            if enabled:
                return f"Interface loopback {STUDENT_ID} is enabled"
            else:
                return f"Interface loopback {STUDENT_ID} is disabled"
        except Exception:
            pass  # ถ้าอ่าน config ไม่ได้ จะลอง operational ต่อ

    # ถ้าไม่เจอใน config → ลอง operational (interfaces-state)
    resp = requests.get(api_status, auth=AUTH, headers=HEADERS, verify=False)
    if resp.status_code == 200:
        try:
            iface = resp.json()["ietf-interfaces:interface"]
            admin = iface.get("admin-status", "unknown")
            oper = iface.get("oper-status", "unknown")

            if admin == "up" and oper == "up":
                return f"Interface loopback {STUDENT_ID} is enabled"
            elif admin == "down" and oper == "down":
                return f"Interface loopback {STUDENT_ID} is disabled"
            else:
                return f"Interface loopback {STUDENT_ID}: admin={admin}, oper={oper}"
        except Exception:
            return f"No Interface loopback {STUDENT_ID}"

    elif cfg.status_code == 404 and resp.status_code == 404:
        return f"No Interface loopback {STUDENT_ID}"

    return f"Error (status): HTTP cfg={cfg.status_code} / op={resp.status_code}"




def dispatch(action, target_ip):
    if action=="create":  return create(target_ip)
    if action=="delete":  return delete(target_ip)
    if action=="enable":  return enable(target_ip)
    if action=="disable": return disable(target_ip)
    if action=="status":  return status(target_ip)
    return "Error: Unknown action"
