# SmartVibe

ระบบเฝ้าระวังความเสียหายโครงสร้าง (Structural Health Monitoring) สำหรับอาคารจำลอง 3 ชั้น
ตรวจจับการเปลี่ยนแปลงของ stiffness จากการเลื่อนของความถี่ธรรมชาติ

**ESP32-S3 + MPU-6050 x3 (ผ่าน TCA9548A) → Firebase Realtime Database → Streamlit Dashboard**

---

## หลักการ

ความถี่ธรรมชาติของโครงสร้างเป็นไปตาม `fn ∝ √(k/m)` เมื่อจุดยึดหลวม stiffness `k` ลดลง
ความถี่ธรรมชาติจึงลดลงตาม วัดอัตราส่วนกลับมาเป็นเปอร์เซ็นต์ความแข็งแรงที่เหลือได้:

```
Health = (fn / fn₀)² × 100  =  % ของ stiffness ที่เหลืออยู่
```

---

## โครงสร้างโปรเจกต์

```
smartvibe/
├── firmware/SmartVibe_ESP32S3/     เฟิร์มแวร์ (Arduino)
│   ├── SmartVibe_ESP32S3.ino       setup/loop — ประกอบร่างอย่างเดียว
│   ├── config.h                    ⚙️ ค่าคงที่ทั้งหมด แก้ที่นี่
│   ├── secrets.h.example           📋 คัดลอกเป็น secrets.h แล้วกรอก
│   ├── types.h                     โครงสร้างข้อมูลร่วม
│   ├── timebase.{h,cpp}            NTP + สร้าง key
│   ├── sensors.{h,cpp}             อ่าน MPU6050 x3
│   ├── uploader.{h,cpp}            คุยกับ Firebase
│   └── tasks.{h,cpp}               แยก sampler/uploader คนละคอร์
│
├── dashboard/                      Streamlit
│   ├── app.py                      จุดเริ่มต้น — ประกอบร่างอย่างเดียว
│   ├── config.py                   ⚙️ ค่าตั้งต้นทั้งหมด แก้ที่นี่
│   ├── core/
│   │   ├── firebase_client.py      ดึงข้อมูลแบบ incremental
│   │   ├── buffer.py               บัฟเฟอร์ rolling ฝั่ง client
│   │   ├── dsp.py                  ประมวลผลสัญญาณ (pure)
│   │   ├── damage.py               Health + เครื่องสถานะ (pure)
│   │   ├── analysis.py             ท่อประมวลผลหลัก
│   │   └── state.py                จัดการ session_state
│   ├── services/
│   │   ├── telegram.py             แจ้งเตือน
│   │   └── ai_assistant.py         ผู้ช่วย AI
│   ├── ui/                         ส่วนแสดงผล (sidebar/floors/charts/debug)
│   └── .streamlit/secrets.toml.example
│
├── tests/                          unit test (15 เคส)
└── docs/SETUP.md                   📖 คู่มือติดตั้งทีละขั้น
```

**หลักการแบ่งโมดูล:** `core/dsp.py` และ `core/damage.py` เป็น pure function
ไม่ import streamlit เลย จึงเขียน unit test ได้โดยตรงและนำไปใช้ที่อื่นได้

---

## เริ่มต้นใช้งาน

อ่านคู่มือแบบละเอียดทีละขั้นที่ **[docs/SETUP.md](docs/SETUP.md)**

สรุปสั้น ๆ:

```bash
git clone https://github.com/<ชื่อผู้ใช้>/smartvibe.git
cd smartvibe

# ---- Dashboard ----
pip install -r requirements.txt
cp dashboard/.streamlit/secrets.toml.example dashboard/.streamlit/secrets.toml
#   แก้ FIREBASE_DOMAIN และ FIREBASE_TOKEN ในไฟล์นั้น
cd dashboard && streamlit run app.py

# ---- Firmware ----
cp firmware/SmartVibe_ESP32S3/secrets.h.example \
   firmware/SmartVibe_ESP32S3/secrets.h
#   กรอก WiFi + Firebase แล้วเปิดใน Arduino IDE กด Upload
```

## รันเทสต์

```bash
pytest tests/ -v
```

---

## ปัญหาที่เวอร์ชันนี้แก้แล้ว

| ปัญหา | สาเหตุ | วิธีแก้ |
|---|---|---|
| Dashboard ค้างที่ "ข้อมูลหยุดนิ่ง" | เฟิร์มแวร์กับ dashboard ชี้คนละฐานข้อมูล | ตั้งค่าที่เดียวใน `secrets` ทั้งสองฝั่ง |
| ส่งสำเร็จแต่ข้อมูลไม่โผล่ | ใช้ `millis()` เป็น key พอ reboot ค่าย้อนกลับ `limitToLast` เลยดึงแต่ข้อมูลเก่า | ใช้ epoch จาก NTP |
| ใช้ไป 2-3 วันแล้วหยุดทำงาน | ดึง 450 record ทุก 1.5 วิ = 4.1 GB/วัน ทะลุโควตาฟรี | incremental fetch ประหยัด ~30 เท่า |
| ลบข้อมูลเก่าไม่ได้ | ring buffer อยู่ใน RAM หายตอน reboot + key เดาไม่ตรง | เก็บ cursor ใน NVS + quantize key |
| ความถี่ที่วัดได้เพี้ยน | HTTPS แบบ blocking ทำให้คาบสุ่มตัวอย่างกระโดด | แยก sampler/uploader คนละคอร์ |
| แอมพลิจูดกระโดดเอง | `nperseg` แปรผัน ทำให้ `df` แกว่ง และลืมคูณ `df` ตอนหา RMS | `nperseg` คงที่ + `sqrt(∫PSD·df)` |
| ค้นหาพีคเหนือ Nyquist | `SEARCH_HI=15` แต่ Nyquist = 10 Hz | บังคับ `hi ≤ 0.45·fs` |

รายละเอียดเชิงเทคนิคอยู่ใน docstring ของแต่ละโมดูล
