# netconf_final.py
import os
from ncclient import manager
import xmltodict
from dotenv import load_dotenv
load_dotenv()

ROUTER_IP = os.environ.get("ROUTER_IP")
NETCONF_PORT = int(os.environ.get("NETCONF_PORT", "830"))
STUDENT_ID = os.environ.get("STUDENT_ID")
IFNAME = f"Loopback{STUDENT_ID}"

m = manager.connect(
    host=ROUTER_IP,
    port=NETCONF_PORT,
    username="admin",
    password="cisco",
    hostkey_verify=False
)

def _ipv4_addr():
    tail3 = int(STUDENT_ID[-3:])
    x = tail3 // 100
    y = tail3 % 100
    return f"172.{x}.{y}.1", "255.255.255.0"

def netconf_edit_config(netconf_config):
    return m.edit_config(target="running", config=netconf_config)

def create():
    ip, mask = _ipv4_addr()
    netconf_config = f"""
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>{IFNAME}</name>
      <description>Loopback for student {STUDENT_ID}</description>
      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:softwareLoopback</type>
      <enabled>true</enabled>
      <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip">
        <address>
          <ip>{ip}</ip>
          <netmask>{mask}</netmask>
        </address>
      </ipv4>
    </interface>
  </interfaces>
</config>
"""
    try:
        netconf_reply = netconf_edit_config(netconf_config)
        if "<ok/>" in netconf_reply.xml:
            return f"Interface loopback {STUDENT_ID} is created successfully"
    except Exception as e:
        print("Error!", e)

def delete():
    netconf_config = f"""
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface operation="delete">
      <name>{IFNAME}</name>
    </interface>
  </interfaces>
</config>
"""
    try:
        netconf_reply = netconf_edit_config(netconf_config)
        if "<ok/>" in netconf_reply.xml:
            return f"Interface loopback {STUDENT_ID} is deleted successfully"
    except Exception as e:
        print("Error!", e)
        return f"Cannot delete: Interface loopback {STUDENT_ID}"

def enable():
    netconf_config = f"""
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>{IFNAME}</name>
      <enabled>true</enabled>
    </interface>
  </interfaces>
</config>
"""
    try:
        netconf_reply = netconf_edit_config(netconf_config)
        if "<ok/>" in netconf_reply.xml:
            return f"Interface loopback {STUDENT_ID} is enabled successfully"
    except Exception as e:
        print("Error!", e)
        return f"Cannot enable: Interface loopback {STUDENT_ID}"

def disable():
    netconf_config = f"""
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>{IFNAME}</name>
      <enabled>false</enabled>
    </interface>
  </interfaces>
</config>
"""
    try:
        netconf_reply = netconf_edit_config(netconf_config)
        if "<ok/>" in netconf_reply.xml:
            return f"Interface loopback {STUDENT_ID} is shutdowned successfully"
    except Exception as e:
        print("Error!", e)
        return f"Cannot shutdown: Interface loopback {STUDENT_ID}"

def status():
    netconf_filter = f"""
<filter>
  <interfaces-state xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>{IFNAME}</name>
    </interface>
  </interfaces-state>
</filter>
"""
    try:
        netconf_reply = m.get(filter=netconf_filter)
        netconf_reply_dict = xmltodict.parse(netconf_reply.xml)
        # หา oper-state ของ interface
        try:
            iface = (netconf_reply_dict["rpc-reply"]["data"]
                     ["interfaces-state"]["interface"])
            admin_status = iface["admin-status"]
            oper_status = iface["oper-status"]
        except Exception:
            return f"No Interface loopback {STUDENT_ID}"
        if admin_status == "up" and oper_status == "up":
            return f"Interface loopback {STUDENT_ID} is enabled"
        elif admin_status == "down" and oper_status == "down":
            return f"Interface loopback {STUDENT_ID} is disabled"
        else:
            return f"Interface loopback {STUDENT_ID}: admin={admin_status}, oper={oper_status}"
    except Exception as e:
        print("Error!", e)
        return f"Error (status)"
