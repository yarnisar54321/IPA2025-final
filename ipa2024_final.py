# ipa2024_final.py
#######################################################################################
# Yourname:
# Your student ID:
# Your GitHub Repo: 
#######################################################################################
# 1. Imports
import os, time, json, requests
from dotenv import load_dotenv
from requests_toolbelt import MultipartEncoder
# เลือกจะใช้ RESTCONF หรือ NETCONF (เอาอันเดียวพอ) และ Netmiko/Ansible
import restconf_final as intf      # ถ้าจะใช้ NETCONF ให้เปลี่ยนเป็น: import netconf_final as intf
import netmiko_final
import ansible_final
load_dotenv()
#######################################################################################
# 2. ACCESS_TOKEN จาก ENV (ห้าม hardcode)
ACCESS_TOKEN = os.environ["WEBEX_ACCESS_TOKEN"]
STUDENT_ID = os.environ["STUDENT_ID"]

#######################################################################################
# 3. Params สำหรับดึงข้อความล่าสุดจากห้อง
roomIdToGetMessages = os.environ["WEBEX_ROOM_ID"]

while True:
    time.sleep(1)
    getParameters = {"roomId": roomIdToGetMessages, "max": 1}
    getHTTPHeader = {"Authorization": ACCESS_TOKEN}

    # 4. เรียก Messages API
    r = requests.get(
        "https://webexapis.com/v1/messages",
        params=getParameters,
        headers=getHTTPHeader,
    )
    if r.status_code != 200:
        raise Exception(f"Incorrect reply from Webex Teams API. Status code: {r.status_code}")

    json_data = r.json()
    if len(json_data.get("items", [])) == 0:
        continue

    message = json_data["items"][0].get("text", "")
    print("Received message:", message)

    # ตรวจรูปแบบ: "/<STUDENT_ID> <command>"
    prefix = f"/{STUDENT_ID} "
    if message.startswith(prefix):
        command = message[len(prefix):].strip()
        print("command:", command)

        # 5. Logic แต่ละคำสั่ง
        if command == "create":
            responseMessage = intf.create()
        elif command == "delete":
            responseMessage = intf.delete()
        elif command == "enable":
            responseMessage = intf.enable()
        elif command == "disable":
            responseMessage = intf.disable()
        elif command == "status":
            responseMessage = intf.status()
        elif command == "gigabit_status":
            responseMessage = netmiko_final.gigabit_status()
        elif command == "showrun":
            responseMessage = ansible_final.showrun()
        else:
            responseMessage = "Error: No command or unknown command"

        # 6. โพสต์กลับไปที่ห้อง (กรณี showrun และสำเร็จ -> แนบไฟล์)
        if command == "showrun" and responseMessage == "ok":
            # ตั้งชื่อไฟล์ที่ playbook เซฟไว้ เช่น show_run_<studentID>_<router>.txt
            # สมมุติ router_name เอาเป็น CSR1KV-PodX-Y (คุณกำหนดใน playbook ให้ตรง)
            router_name = "CSR1KV-PodX-Y"   # แก้ให้ตรงกับของจริงหรืออ่านจากไฟล์ก็ได้
            filename = f"show_run_{STUDENT_ID}_{router_name}.txt"
            fileobject = open(filename, "rb")
            filetype = "text/plain"

            postData = {
                "roomId": roomIdToGetMessages,
                "text": "show running config",
                "files": (filename, fileobject, filetype),
            }
            postData = MultipartEncoder(postData)
            HTTPHeaders = {
                "Authorization": ACCESS_TOKEN,
                "Content-Type": postData.content_type,
            }
            r = requests.post(
                "https://webexapis.com/v1/messages",
                data=postData,
                headers=HTTPHeaders,
            )
            fileobject.close()
            if r.status_code != 200:
                raise Exception(f"Incorrect reply from Webex Teams API. Status code: {r.status_code}")
        else:
            postData = {"roomId": roomIdToGetMessages, "text": responseMessage}
            HTTPHeaders = {"Authorization": ACCESS_TOKEN, "Content-Type": "application/json"}
            r = requests.post(
                "https://webexapis.com/v1/messages",
                data=json.dumps(postData),
                headers=HTTPHeaders,
            )
            if r.status_code != 200:
                raise Exception(f"Incorrect reply from Webex Teams API. Status code: {r.status_code}")
