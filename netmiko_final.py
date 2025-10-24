#netmiko_final.py
from netmiko import ConnectHandler
from pprint import pprint

# กำหนดค่าการเชื่อมต่อ Router
device_ip = "10.0.15.61"      # แก้เป็น IP Router ของคุณ (.61–.65 ตาม Pod)
username = "admin"
password = "cisco"

device_params = {
    "device_type": "cisco_ios",  # อุปกรณ์เป็น Cisco IOS XE
    "ip": device_ip,
    "username": username,
    "password": password,
}

def gigabit_status():
    try:
        with ConnectHandler(**device_params) as ssh:
            # ใช้ TextFSM เพื่อแปลงผลลัพธ์เป็น list of dict
            result = ssh.send_command("show ip interface brief", use_textfsm=True)

            up = 0
            down = 0
            admin_down = 0
            parts = []

            for row in result:
                intf = row.get("interface") or row.get("intf")
                status = row.get("status")

                # ตรวจเฉพาะ GigabitEthernet interfaces
                if intf and intf.startswith("GigabitEthernet"):
                    parts.append(f"{intf} {status}")
                    if status == "up":
                        up += 1
                    elif status == "down":
                        down += 1
                    elif status == "administratively down":
                        admin_down += 1

            # รวมข้อความตามรูปแบบที่โจทย์ต้องการ
            ans = ", ".join(parts) + f" -> {up} up, {down} down, {admin_down} administratively down"

            pprint(ans)
            return ans

    except Exception as e:
        return f"Error (Netmiko): {str(e)}"

