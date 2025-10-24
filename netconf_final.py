# netconf_final.py
import os
from ncclient import manager
import xmltodict
from dotenv import load_dotenv
load_dotenv()

NETCONF_PORT = int(os.environ.get("NETCONF_PORT","830"))
STUDENT_ID   = os.environ.get("STUDENT_ID")
IFNAME       = f"Loopback{STUDENT_ID}"

def _ipv4_addr():
    tail3 = int(STUDENT_ID[-3:])
    x = tail3 // 100
    y = tail3 % 100
    return f"172.{x}.{y}.1", "255.255.255.0"

def _connect(ip):
    return manager.connect(
        host=ip, port=NETCONF_PORT,
        username="admin", password="cisco",
        hostkey_verify=False, timeout=15
    )

def create(ip):
    ipaddr, mask = _ipv4_addr()
    xml = f"""
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>{IFNAME}</name>
      <description>Loopback for student {STUDENT_ID}</description>
      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:softwareLoopback</type>
      <enabled>true</enabled>
      <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip">
        <address><ip>{ipaddr}</ip><netmask>{mask}</netmask></address>
      </ipv4>
    </interface>
  </interfaces>
</config>"""
    try:
        with _connect(ip) as m:
            r = m.edit_config(target="running", config=xml)
            if "<ok/>" in r.xml:
                return f"Interface loopback {STUDENT_ID} is created successfully"
    except Exception:
        return f"Cannot create: Interface loopback {STUDENT_ID}"

def delete(ip):
    xml = f"""
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface operation="delete">
      <name>{IFNAME}</name>
    </interface>
  </interfaces>
</config>"""
    try:
        with _connect(ip) as m:
            r = m.edit_config(target="running", config=xml)
            if "<ok/>" in r.xml:
                return f"Interface loopback {STUDENT_ID} is deleted successfully"
    except Exception:
        return f"Cannot delete: Interface loopback {STUDENT_ID}"

def enable(ip):
    xml = f"""
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>{IFNAME}</name>
      <enabled>true</enabled>
    </interface>
  </interfaces>
</config>"""
    try:
        with _connect(ip) as m:
            r = m.edit_config(target="running", config=xml)
            if "<ok/>" in r.xml:
                return f"Interface loopback {STUDENT_ID} is enabled successfully"
    except Exception:
        return f"Cannot enable: Interface loopback {STUDENT_ID}"

def disable(ip):
    xml = f"""
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>{IFNAME}</name>
      <enabled>false</enabled>
    </interface>
  </interfaces>
</config>"""
    try:
        with _connect(ip) as m:
            r = m.edit_config(target="running", config=xml)
            if "<ok/>" in r.xml:
                return f"Interface loopback {STUDENT_ID} is shutdowned successfully"
    except Exception:
        return f"Cannot shutdown: Interface loopback {STUDENT_ID} (checked by Netconf)"

def status(ip):
    flt = f"""
<filter>
  <interfaces-state xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface><name>{IFNAME}</name></interface>
  </interfaces-state>
</filter>"""
    try:
        with _connect(ip) as m:
            r = m.get(filter=flt)
            d = xmltodict.parse(r.xml)

            # ถ้าไม่มีข้อมูลใน reply -> interface ไม่มีจริง
            if not d.get("rpc-reply", {}).get("data"):
                return f"No Interface loopback {STUDENT_ID}"

            try:
                iface = d["rpc-reply"]["data"]["interfaces-state"]["interface"]
            except Exception:
                return f"No Interface loopback {STUDENT_ID}"

            admin = iface.get("admin-status", "unknown")
            oper = iface.get("oper-status", "unknown")

            if admin == "up" and oper == "up":
                return f"Interface loopback {STUDENT_ID} is enabled"
            elif admin == "down" and oper == "down":
                return f"Interface loopback {STUDENT_ID} is disabled"
            else:
                return f"Interface loopback {STUDENT_ID}: admin={admin}, oper={oper}"

    except Exception as e:
        return f"Error (status): {str(e)}"


def dispatch(action, target_ip):
    if action=="create":  return create(target_ip)
    if action=="delete":  return delete(target_ip)
    if action=="enable":  return enable(target_ip)
    if action=="disable": return disable(target_ip)
    if action=="status":  return status(target_ip)
    return "Error: Unknown action"
