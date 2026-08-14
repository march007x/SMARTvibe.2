# คู่มือติดตั้ง SmartVibe ตั้งแต่ต้นจนจบ

อ่านตามลำดับ ห้ามข้ามขั้น แต่ละส่วนมี **✅ จุดตรวจสอบ** ให้ยืนยันก่อนไปต่อ
ถ้าจุดตรวจสอบไม่ผ่าน อย่าเพิ่งไปขั้นถัดไป ให้ดูตารางแก้ปัญหาท้ายเอกสาร

---

## สารบัญ

| ส่วน | เนื้อหา | เวลาโดยประมาณ |
|---|---|---|
| [0](#ส่วนที่-0-เตรียมของ) | เตรียมของ | 10 นาที |
| [1](#ส่วนที่-1-ตั้งค่า-firebase) | ตั้งค่า Firebase | 15 นาที |
| [2](#ส่วนที่-2-เตรียม-repo-บน-github) | เตรียม repo บน GitHub | 10 นาที |
| [3](#ส่วนที่-3-แฟลชเฟิร์มแวร์) | แฟลชเฟิร์มแวร์ | 30 นาที |
| [4](#ส่วนที่-4-รัน-dashboard-บนเครื่อง) | รัน Dashboard | 15 นาที |
| [5](#ส่วนที่-5-แจ้งเตือน-telegram) | แจ้งเตือน Telegram | 10 นาที |
| [6](#ส่วนที่-6-ผู้ช่วย-ai) | ผู้ช่วย AI | 10 นาที |
| [7](#ส่วนที่-7-deploy-ขึ้น-streamlit-cloud) | Deploy ขึ้นคลาวด์ | 15 นาที |
| [8](#ส่วนที่-8-ขั้นตอนการทดลองจริง) | **ขั้นตอนการทดลองจริง** | 30 นาที |
| [9](#ส่วนที่-9-แก้ปัญหา) | ตารางแก้ปัญหา | — |

---

# ส่วนที่ 0: เตรียมของ

## 0.1 ฮาร์ดแวร์

- ESP32-S3 (รุ่น N16R8 หรือใกล้เคียง) + สาย USB-C ที่ **ส่งข้อมูลได้** (สายชาร์จอย่างเดียวใช้ไม่ได้)
- MPU-6050 x 3 ตัว
- TCA9548A I2C multiplexer x 1
- สายจัมเปอร์, อาคารจำลอง 3 ชั้น

**การต่อสาย**

| จาก | ไป | หมายเหตุ |
|---|---|---|
| ESP32-S3 GPIO 8 | TCA9548A SDA | เปลี่ยนได้ที่ `config.h` → `I2C_SDA` |
| ESP32-S3 GPIO 9 | TCA9548A SCL | เปลี่ยนได้ที่ `config.h` → `I2C_SCL` |
| ESP32-S3 3V3 | TCA9548A VIN | |
| ESP32-S3 GND | TCA9548A GND | |
| TCA9548A SD0/SC0 | MPU ชั้น 1 | ช่อง 0 |
| TCA9548A SD1/SC1 | MPU ชั้น 2 | ช่อง 1 |
| TCA9548A SD2/SC2 | MPU ชั้น 3 (ดาดฟ้า) | ช่อง 2 |

> ติด MPU ให้ **แกน X ชี้ไปทางเดียวกันทั้ง 3 ตัว** และขนานกับทิศที่ตึกจะแกว่ง
> ระบบใช้เฉพาะ `AccX` ในการวิเคราะห์ ถ้าติดคนละทิศ Transmissibility จะผิด

## 0.2 ซอฟต์แวร์

| โปรแกรม | ใช้ทำอะไร | ที่มา |
|---|---|---|
| Arduino IDE 2.x | คอมไพล์และแฟลชเฟิร์มแวร์ | arduino.cc |
| Python 3.10+ | รัน dashboard | python.org |
| Git | ดึง/ส่งโค้ด | git-scm.com |
| บัญชี Google | สร้าง Firebase | — |
| บัญชี GitHub | เก็บโค้ด | — |

**✅ จุดตรวจสอบ 0** — เปิด terminal พิมพ์:
```bash
python --version    # ต้องได้ 3.10 ขึ้นไป
git --version       # ต้องมีเลขเวอร์ชัน
```

---

# ส่วนที่ 1: ตั้งค่า Firebase

> ⚠️ ถ้าเคยมีโปรเจกต์เดิมอยู่แล้ว **แนะนำให้สร้างใหม่** เพราะ DB เก่ามีข้อมูลขยะที่คีย์เป็น `millis()`
> ปนอยู่ ซึ่งจะไปยึดครองพื้นที่ query จนข้อมูลใหม่ไม่โผล่ (นี่คือบั๊กเดิม)

## 1.1 สร้างโปรเจกต์

1. เปิด https://console.firebase.google.com
2. **Add project** → ตั้งชื่อเช่น `smartvibe-2569`
3. Google Analytics: **ปิด** (ไม่ต้องใช้ ทำให้ตั้งค่าเร็วขึ้น)
4. รอสร้างเสร็จ → **Continue**

## 1.2 สร้าง Realtime Database

1. เมนูซ้าย → **Build** → **Realtime Database** → **Create Database**
2. **Location: `asia-southeast1` (Singapore)** ← เลือกอันนี้ ใกล้ไทยที่สุด latency ต่ำสุด
3. Security rules: เลือก **Start in test mode** (เดี๋ยวแก้ในขั้น 1.4)
4. กด Enable

## 1.3 คัดลอก Database URL

หน้า Data จะมี URL แบบนี้:
```
https://smartvibe-2569-default-rtdb.asia-southeast1.firebasedatabase.app/
```

📋 **จดไว้ โดยตัด `https://` ข้างหน้า และ `/` ข้างท้ายออก:**
```
smartvibe-2569-default-rtdb.asia-southeast1.firebasedatabase.app
```
เรียกค่านี้ว่า **`FIREBASE_DOMAIN`** จะใช้ทั้งสองฝั่ง

## 1.4 ตั้ง Security Rules

แท็บ **Rules** → วางทับของเดิม → **Publish**

```json
{
  "rules": {
    ".read": "auth != null",
    ".write": "auth != null",
    "History3F": {
      ".indexOn": "$key"
    }
  }
}
```

> `".indexOn": "$key"` สำคัญมาก — ทำให้ query `orderBy="$key"` เร็วขึ้นหลายเท่า
> ถ้าไม่ใส่ Firebase จะเตือนใน console และดึงข้อมูลช้า

## 1.5 เอา Database Secret

1. คลิก **⚙️** ข้าง Project Overview → **Project settings**
2. แท็บ **Service accounts** → เมนูซ้าย **Database secrets**
3. กด **Show** ตรงบรรทัดที่มี → คัดลอก

📋 จดไว้ เรียกว่า **`FIREBASE_TOKEN`**

> 🔒 **สำคัญมาก:** ค่านี้คือกุญแจเข้าฐานข้อมูลแบบเต็มสิทธิ์
> **ห้ามใส่ในไฟล์ที่ push ขึ้น GitHub เด็ดขาด** โปรเจกต์นี้จึงแยกไว้ใน
> `secrets.h` / `secrets.toml` ซึ่งอยู่ใน `.gitignore` แล้ว
>
> ถ้าเคยเผลอ push ไปแล้ว ให้กลับมาหน้านี้ **สร้าง secret ใหม่แล้วลบอันเก่า** ทันที

**✅ จุดตรวจสอบ 1** — คุณต้องมี 2 ค่านี้จดไว้:
- `FIREBASE_DOMAIN` = `xxxxx-default-rtdb.asia-southeast1.firebasedatabase.app`
- `FIREBASE_TOKEN` = สตริงยาว ๆ ประมาณ 40 ตัวอักษร

---

# ส่วนที่ 2: เตรียม repo บน GitHub

## 2.1 สร้าง repo

1. https://github.com/new
2. Repository name: `smartvibe`
3. **เลือก Private** (แม้ความลับจะถูกกันไว้แล้ว แต่ private ปลอดภัยกว่า)
4. ไม่ต้องติ๊ก Add README (เรามีแล้ว)
5. **Create repository**

## 2.2 อัปโหลดโค้ด

```bash
cd smartvibe

git init
git add .
git commit -m "SmartVibe: โครงสร้างแบบแยกโมดูล"
git branch -M main
git remote add origin https://github.com/<ชื่อผู้ใช้>/smartvibe.git
git push -u origin main
```

## 2.3 ⚠️ ตรวจว่าความลับไม่หลุด

```bash
git ls-files | grep -E "secrets\.(h|toml)$"
```

**ต้องไม่มีผลลัพธ์ออกมา** ถ้ามี แปลว่า `.gitignore` ไม่ทำงาน ให้แก้ทันที:

```bash
git rm --cached firmware/SmartVibe_ESP32S3/secrets.h
git rm --cached dashboard/.streamlit/secrets.toml
git commit -m "เอาความลับออกจาก git"
git push
```
แล้วกลับไปขั้น 1.5 **สร้าง Firebase secret ใหม่** เพราะอันเก่าถือว่ารั่วแล้ว

**✅ จุดตรวจสอบ 2** — เปิดหน้า repo บนเว็บ เห็นโฟลเดอร์ `firmware/`, `dashboard/`, `tests/`, `docs/`
และ **ไม่เห็น** `secrets.h` หรือ `secrets.toml`

---

# ส่วนที่ 3: แฟลชเฟิร์มแวร์

## 3.1 ติดตั้ง ESP32 board package

1. เปิด Arduino IDE → **File → Preferences**
2. ช่อง *Additional boards manager URLs* วาง:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. **Tools → Board → Boards Manager** → ค้น `esp32` → ติดตั้ง **esp32 by Espressif Systems**
4. **Tools → Board → ESP32 Arduino → ESP32S3 Dev Module**

## 3.2 ติดตั้งไลบรารี

**Tools → Manage Libraries** ค้นและติดตั้ง 2 ตัว:

| ชื่อ | ผู้พัฒนา |
|---|---|
| `Firebase Arduino Client Library for ESP8266 and ESP32` | Mobizt |
| `MPU6050_tockn` | tockn |

## 3.3 สร้าง secrets.h

```bash
cd firmware/SmartVibe_ESP32S3
cp secrets.h.example secrets.h
```

เปิด `secrets.h` แก้ 4 บรรทัด:

```cpp
#define WIFI_SSID      "ชื่อ WiFi ของโรงเรียน"
#define WIFI_PASSWORD  "รหัสผ่าน"
#define FIREBASE_AUTH  "FIREBASE_TOKEN จากขั้น 1.5"
#define FIREBASE_HOST  "FIREBASE_DOMAIN จากขั้น 1.3"
```

> ⚠️ ESP32 ต่อได้เฉพาะ **WiFi 2.4 GHz** เท่านั้น ถ้าเราเตอร์แยก SSID ของ 5 GHz ไว้
> ต้องเลือกอันที่เป็น 2.4 GHz
>
> ⚠️ WiFi ของโรงเรียนที่ต้องล็อกอินผ่านหน้าเว็บ (captive portal) **ใช้ไม่ได้**
> ให้ใช้ hotspot จากมือถือแทนตอนทดสอบ

## 3.4 ตั้งค่าบอร์ดใน Arduino IDE

เมนู **Tools** ตั้งตามนี้:

| หัวข้อ | ค่า | เหตุผล |
|---|---|---|
| Board | ESP32S3 Dev Module | |
| USB CDC On Boot | **Enabled** | ⚠️ ไม่เปิดจะไม่เห็นข้อความใน Serial Monitor เลย |
| Flash Size | 16MB (128Mb) | ตามรุ่น N16R8 |
| PSRAM | OPI PSRAM | ตามรุ่น N16R8 |
| Partition Scheme | 16M Flash (3MB APP/9.9MB FATFS) | |
| Upload Speed | 921600 | ถ้าแฟลชไม่ผ่าน ลดเป็น 115200 |

## 3.5 แฟลช

1. เปิด `firmware/SmartVibe_ESP32S3/SmartVibe_ESP32S3.ino`
   (ไฟล์ `.h`/`.cpp` ในโฟลเดอร์เดียวกันจะถูกคอมไพล์อัตโนมัติ ไม่ต้องเปิดเอง)
2. เสียบ USB → **Tools → Port** เลือกพอร์ตที่โผล่ขึ้นมา
3. กด **Upload** (→)
4. ถ้าค้างที่ `Connecting...` ให้กดปุ่ม **BOOT** บนบอร์ดค้างไว้ แล้วกด **RESET** หนึ่งที ปล่อย RESET แล้วปล่อย BOOT

## 3.6 อ่าน Serial Monitor

**Tools → Serial Monitor** → ตั้ง baud **115200**

**วางบอร์ดนิ่ง ๆ** ตอน calibrate gyro (~10 วินาที) แล้วควรเห็น:

```
===== SmartVibe =====
ตั้งค่าเซ็นเซอร์ชั้น 1 (CH0)...
ตั้งค่าเซ็นเซอร์ชั้น 2 (CH1)...
ตั้งค่าเซ็นเซอร์ชั้น 3 (CH2)...
✅ MPU6050 x3 พร้อมใช้งาน
CH0: 0x68
CH1: 0x68
CH2: 0x68
เชื่อมต่อ WiFi....
✅ WiFi IP: 192.168.1.42  RSSI: -52 dBm
📡 DB: smartvibe-2569-default-rtdb.asia-southeast1.firebasedatabase.app
sync NTP...
✅ NTP ok — epoch_ms = 1755158400000
✅ SmartVibe พร้อมทำงาน

🚀 [OK] n=25 | 312ms | heap=241556 | rssi=-52
🗑️  cleanup 200 keys → 1755158345000
```

**อ่านค่าแต่ละอย่างอย่างไร:**

| สิ่งที่เห็น | ความหมาย | เกณฑ์ที่ดี |
|---|---|---|
| `CH0/1/2: 0x68` | เจอ MPU ครบ 3 ตัว | ถ้าช่องไหนขึ้น "❌ ไม่พบอุปกรณ์" = สายช่องนั้นหลุด |
| `rssi=-52` | ความแรง WiFi | ดี > -70 · ใช้ได้ -70 ถึง -80 · แย่ < -80 |
| `312ms` | เวลาที่ใช้ส่ง 1 batch | ควร < 500 ms |
| `heap=241556` | หน่วยความจำเหลือ | ต้องไม่ลดลงเรื่อย ๆ ถ้าลดคือ memory leak |
| `🗑️ cleanup` | ลบข้อมูลเก่าสำเร็จ | ต้องเห็นทุก ~15 วินาที |

## 3.7 ✅ จุดตรวจสอบ 3 — ยืนยันข้อมูลเข้า Firebase จริง

กลับไป Firebase Console → Realtime Database → Data

**ต้องเห็น 2 อย่าง:**

1. `History3F` มีคีย์ 13 หลักเรียงต่อกัน เช่น `1755158400000`, `1755158400020`, ...
2. `History3F_meta/heartbeat` มี `server_ts` ที่ **ขยับทุก 5 วินาที** (กด refresh หน้าเว็บดู)

> 🔍 **heartbeat คือเครื่องมือหลักในการไล่จับปัญหา**
> - `server_ts` ขยับ = บอร์ดส่งถึงจริง ปัญหาอยู่ที่ dashboard
> - `server_ts` ไม่ขยับ ทั้งที่ Serial ขึ้น `[OK]` = SDK รายงานสำเร็จปลอม
>   (ดูส่วนที่ 9 ข้อ D)

---

# ส่วนที่ 4: รัน Dashboard บนเครื่อง

## 4.1 ติดตั้ง Python packages

```bash
cd smartvibe

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## 4.2 สร้าง secrets.toml

```bash
cd dashboard
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

เปิด `.streamlit/secrets.toml` แก้ 2 บรรทัดแรก:

```toml
FIREBASE_DOMAIN = "smartvibe-2569-default-rtdb.asia-southeast1.firebasedatabase.app"
FIREBASE_TOKEN  = "ค่าเดียวกับที่ใส่ใน secrets.h"
```

> 🔴 **นี่คือจุดที่พังบ่อยที่สุด** — ค่า `FIREBASE_DOMAIN` ตรงนี้ต้องเหมือน `FIREBASE_HOST`
> ใน `secrets.h` **ตัวอักษรต่อตัวอักษร** บั๊กเดิมของโปรเจกต์นี้คือสองฝั่งชี้คนละฐานข้อมูล
> ทำให้ dashboard อ่านข้อมูลค้างของ DB เก่าตลอดเวลา
>
> วิธีตรวจง่าย ๆ: คัดลอกจาก `secrets.h` มาวางเลย อย่าพิมพ์ใหม่

## 4.3 รัน

```bash
streamlit run app.py
```

เบราว์เซอร์จะเปิด `http://localhost:8501`

## 4.4 ✅ จุดตรวจสอบ 4

ลำดับสิ่งที่ควรเห็น:

1. **10 วินาทีแรก**: "⏳ กำลังรอข้อมูลจากเซ็นเซอร์... (ได้ N จุด)" — ตัวเลข N ต้องเพิ่มขึ้น
2. **หลังได้ 100 จุด**: แถบฟ้าขึ้น `📡 fs จริง ≈ 50.0 Hz (Nyquist 25.0 Hz)`
3. เห็นการ์ด 3 ชั้น มีค่า RMS ไม่เป็น 0
4. กราฟ PSD ด้านล่างมีเส้น 3 เส้น

**ถ้าค้างที่ข้อ 1 ไม่ขยับ** → กด **🔍 ตรวจ heartbeat ของบอร์ด** ใน sidebar
- ได้ JSON กลับมา = เชื่อมต่อถูก แต่ query มีปัญหา → ตรวจ `DB_PATH` ทั้งสองฝั่ง
- ขึ้น error = `FIREBASE_DOMAIN` หรือ `FIREBASE_TOKEN` ผิด

---

# ส่วนที่ 5: แจ้งเตือน Telegram

## 5.1 สร้าง bot

1. เปิด Telegram → ค้นหา **@BotFather** → เริ่มแชท
2. พิมพ์ `/newbot`
3. ตั้งชื่อ bot เช่น `SmartVibe Alert`
4. ตั้ง username ที่ **ลงท้ายด้วย `bot`** เช่น `smartvibe_prot_bot`
5. BotFather จะส่ง token มา หน้าตาแบบ `123456789:AAH-xxxxxxxxxxxxx`

📋 จดไว้ = **`TELEGRAM_TOKEN`**

## 5.2 หา chat_id

**ส่งหาตัวเอง:**
1. ค้นหา **@userinfobot** → กด Start
2. มันจะตอบ `Id: 987654321` ← นั่นคือ `TELEGRAM_CHAT_ID`

**ส่งเข้ากลุ่ม (เช่น กลุ่มครูวิทย์):**
1. เพิ่ม bot ที่สร้างเข้ากลุ่ม
2. เพิ่ม **@RawDataBot** เข้ากลุ่มด้วย
3. พิมพ์อะไรก็ได้ในกลุ่ม → RawDataBot จะแสดง `"chat": {"id": -1001234567890}`
4. ใช้ตัวเลขนั้น **รวมเครื่องหมายลบ**
5. ลบ RawDataBot ออกจากกลุ่ม

## 5.3 ใส่ค่า

แก้ `dashboard/.streamlit/secrets.toml` เอา `#` ออกแล้วกรอก:

```toml
TELEGRAM_TOKEN   = "123456789:AAH-xxxxxxxxxxxxx"
TELEGRAM_CHAT_ID = "987654321"
```

## 5.4 ✅ จุดตรวจสอบ 5

รีสตาร์ท Streamlit (Ctrl+C แล้วรันใหม่) → sidebar ต้องขึ้น **"Telegram พร้อมใช้งาน"**
→ กด **ส่งข้อความทดสอบ** → ต้องได้ข้อความใน Telegram

## 5.5 เงื่อนไขที่จะแจ้งเตือน

| เหตุการณ์ | ข้อความ |
|---|---|
| ชั้นใดเปลี่ยนเป็น 🔴 | เตือนภัย + Health % |
| ชั้นใดเปลี่ยนเป็น 🟡 | เฝ้าระวัง |
| ชั้นใดฟื้นเป็น 🟢 | กลับสู่ปกติ |
| ข้อมูลหยุดนิ่ง ≥ 4 รอบ | พร้อมรายการสิ่งที่ต้องตรวจ |
| Health ตก ≥ 15% ใน 10 นาที | Health ร่วงเร็ว |

ปรับเกณฑ์ได้ที่ `dashboard/services/telegram.py` บรรทัดบนสุด:
```python
COOLDOWN_SEC    = 300     # ห้ามส่ง event เดิมซ้ำใน 5 นาที
HEALTH_DROP_PCT = 15.0
HEALTH_WINDOW_S = 600.0
```

---

# ส่วนที่ 6: ผู้ช่วย AI

## 6.1 เลือกผู้ให้บริการ

| | ความเร็ว | โควตาฟรี | ใช้บน Streamlit Cloud ได้ | เหมาะกับ |
|---|---|---|---|---|
| **Groq** ⭐ | เร็วมาก | ~14,000 req/วัน | ✅ | ทุกกรณี — แนะนำ |
| OpenRouter | ปานกลาง | ~50 req/วัน | ✅ | สำรอง |
| Ollama | ขึ้นกับเครื่อง | ไม่จำกัด | ❌ | รันในโรงเรียนแบบออฟไลน์ |

## 6.2 ขอ API key จาก Groq

1. https://console.groq.com → สมัครด้วย Google
2. เมนูซ้าย **API Keys** → **Create API Key**
3. คัดลอก (แสดงครั้งเดียว)
4. ใส่ใน `secrets.toml`:
   ```toml
   GROQ_API_KEY = "gsk_xxxxxxxxxxxx"
   ```

## 6.3 ถ้าจะใช้ Ollama (ออฟไลน์)

```bash
# ติดตั้งจาก ollama.com
ollama pull qwen2.5:7b     # ~4.7 GB ต้องมี RAM ≥ 8 GB
ollama serve
```
แล้วเลือก "Ollama (เครื่องตัวเอง)" ใน dropdown ไม่ต้องใส่ key

## 6.4 ✅ จุดตรวจสอบ 6

เลื่อนลงไปหัวข้อ **🤖 ผู้ช่วย AI วิเคราะห์** → กด **🔍 วิเคราะห์สถานะตอนนี้**
→ ควรได้คำตอบภาษาไทยภายใน 3-5 วินาที

> 💡 ปุ่มนี้เป็น **on-demand เท่านั้น** ไม่เรียก AI อัตโนมัติทุก 1.5 วินาที
> เพราะจะทำให้โควตาหมดภายใน 6 นาที และคำตอบถูก cache ไว้ 5 นาที
> ถ้าสถานะไม่เปลี่ยนก็ไม่เรียก API ซ้ำ

---

# ส่วนที่ 7: Deploy ขึ้น Streamlit Cloud

> ทำเมื่อต้องการให้คนอื่นเปิดดูได้จากที่ไหนก็ได้ (เช่น กรรมการตอนนำเสนอ)

1. https://share.streamlit.io → **Sign in with GitHub**
2. **New app** → เลือก repo `smartvibe`
3. **Main file path:** ต้องใส่ `dashboard/app.py` ← ไม่ใช่แค่ `app.py`
4. **Advanced settings → Secrets** → วางเนื้อหาทั้งหมดของ `secrets.toml` ลงไป
   (ห้าม push ไฟล์ขึ้น GitHub ให้วางในช่องนี้แทน)
5. **Deploy** รอ 3-5 นาที

**✅ จุดตรวจสอบ 7** — เปิด URL ที่ได้จากมือถือ ต้องเห็นข้อมูลเหมือนบนเครื่อง

> ⚠️ Streamlit Cloud จะพักแอปเมื่อไม่มีคนใช้ 7 วัน ก่อนวันนำเสนอให้เข้าไปเปิดสักครั้ง
>
> ⚠️ ถ้า deploy แล้ว error `ModuleNotFoundError: No module named 'config'`
> แปลว่าใส่ Main file path ผิด ต้องเป็น `dashboard/app.py`

---

# ส่วนที่ 8: ขั้นตอนการทดลองจริง

> 📌 **ส่วนนี้สำคัญที่สุด** — เป็นการแก้ปัญหา "แอมพลิจูดชั้นที่เสียหายลดลงทั้งที่ทฤษฎีบอกว่าควรพุ่ง"

## 8.1 ทำไมวิธีเดิม (ลำโพงยิง sine ความถี่เดียว) ถึงให้ผลกลับด้าน

ถ้าจูนลำโพงให้ตรงเรโซแนนซ์ตอนล็อก baseline (`f_drive = fn₀`) แล้วโครงสร้างเปลี่ยน:

```
        amp                 baseline: อ่านที่ยอดพีคพอดี
         │      ╱▲╲
         │     ╱ │ ╲          พีคเลื่อนไป (ซ้ายหรือขวาก็ได้)
         │   ╱   │   ╲   ╱▲╲
         │ ╱     │     ╳   │ ╲
         └───────┼─────────┴──── f
              f_drive
                 ↑ อ่านที่จุดเดิมตลอด → ได้ค่าลาดลงเสมอ
```

ผลจากการจำลอง (SDOF, ζ=0.03, ขับที่ 8 Hz):

| กรณี | fn จริง | แอมพลิจูดที่ f_drive |
|---|---|---|
| baseline | 8.00 Hz | 26.66 |
| คลายน็อต −20% k | 7.16 Hz | 6.18 ⬇️ |
| คลายน็อต −40% k | 6.20 Hz | 2.39 ⬇️⬇️ |
| **ขันแน่น +25% k** | 8.94 Hz | **7.73 ⬇️** |

**คลายก็ตก ขันแน่นก็ตก** — วัดแบบนี้บอกทิศทางความเสียหายไม่ได้เลย

ที่สำคัญ: ภายใต้ sine บริสุทธิ์ในสถานะคงตัว **fn ของตึกไม่ปรากฏในสเปกตรัมเลย**
มีแต่ f_drive อย่างเดียว → **แก้ที่โค้ดไม่ได้ ต้องเปลี่ยนวิธีกระตุ้น**

## 8.2 ✅ วิธีที่ถูกต้อง: การเคาะกระแทก (impulse test)

ดีกว่า white noise สำหรับโปรเจกต์นักเรียนเพราะไม่ต้องใช้ลำโพงเลย และทำซ้ำได้แม่นกว่า

**ขั้นตอน**

1. sidebar → เลือกโหมด **"ติดตาม fn (White Noise/Sweep/เคาะ)"**
2. ประกอบตึกให้สมบูรณ์ ขันน็อตทุกตัวแน่นเท่ากัน
3. **เคาะดาดฟ้าเบา ๆ ทางด้านข้าง** (ทิศเดียวกับแกน X ของ MPU) แล้วปล่อยให้แกว่งอิสระ
4. เคาะซ้ำทุก ~5 วินาที ให้ RMS อยู่เหนือเกณฑ์ตลอด — สังเกตให้แถบบนขึ้น "แรงกระตุ้น ✅ ปกติ"
5. รอ **20-30 วินาที** ให้ค่า fn นิ่ง (median filter ใช้ 7 จุด)
6. เมื่อ fn ของทั้ง 3 ชั้นแกว่งไม่เกิน ±0.05 Hz → กด **🔒 ล็อก Baseline**
7. จดค่า `fn₀` ทั้ง 3 ชั้นไว้ในสมุดบันทึกการทดลอง

**ทดสอบความเสียหาย**

8. **คลายน็อต** ของชั้นใดชั้นหนึ่ง (เช่น ชั้น 2) ประมาณ 1/4 รอบ
9. เคาะซ้ำแบบเดิม รอ 20-30 วินาที
10. บันทึก: `fn` ใหม่, `Health %`, สถานะสี, `Δf` ที่แสดงใต้ค่า fn

**สิ่งที่ควรเห็น**

| ปริมาณ | ทิศทางที่คาดหวัง |
|---|---|
| fn ของชั้นที่คลาย | **ลดลง** |
| Health % ของชั้นนั้น | **ลดลง** ≈ (fn/fn₀)² |
| แอมพลิจูดที่พีคใหม่ | **เพิ่มขึ้น** ← ตรงกับทฤษฎีแล้ว |
| ชั้นอื่น ๆ | เปลี่ยนน้อยมาก |

> ✔️ ผมทดสอบ pipeline ด้วยข้อมูลจำลองแล้ว: จำลอง `k` ลด 20% → fn ลดจาก 8.00 เป็น 7.16 Hz
> → Health อ่านได้ **80.1%** (ทฤษฎีบอก 80%) และสถานะเปลี่ยนเป็น 🟡 หลังผ่านเกณฑ์ติดกัน 3 รอบ

## 8.3 โบนัสสำหรับการแข่งขัน: Damping ratio

การเคาะกระแทกให้ข้อมูลที่ลำโพงให้ไม่ได้ — **อัตราการหน่วง ζ**
น็อตหลวมทำให้เกิดการเสียดสี ζ จะพุ่งขึ้นชัดกว่า fn เสียอีก

หาได้จาก logarithmic decrement ของช่วง free decay:

```
δ = (1/n) · ln(x₀/xₙ)        ζ = δ / √(4π² + δ²)
```

ตัวชี้วัดคู่ **`Health = (fn/fn₀)²`** และ **`Damage index = ζ/ζ₀`** เป็นมาตรฐาน SHM จริง
ใช้อธิบายกรรมการได้ว่าไม่ได้คิดเอง (ยังไม่ได้ implement ในเวอร์ชันนี้)

## 8.4 ถ้ายังอยากใช้ลำโพง

| วิธีกระตุ้น | ใช้โหมด | ตัวชี้วัด | ตามล่า fn ได้ไหม |
|---|---|---|---|
| เคาะกระแทก | ติดตาม fn | Health = (fn/fn₀)² | ✅ |
| White noise | ติดตาม fn | Health = (fn/fn₀)² | ✅ |
| Chirp sweep 2-20 Hz | ติดตาม fn | Health = (fn/fn₀)² | ✅ |
| Sine ความถี่เดียว | ไซน์คงที่ | Transmissibility | ❌ |

> โหมดไซน์ยังใช้ได้ผลนะครับ แค่ต้องตีความว่ากำลังวัด **"อัตราส่วนการสั่นระหว่างชั้นเปลี่ยนไปไหม"**
> ไม่ใช่ "ตึกแข็งขึ้นหรืออ่อนลง" และเวอร์ชันนี้เพิ่ม **coherence** มาบอกด้วยว่าข้อมูลรอบนั้นเชื่อได้ไหม
> (coherence < 0.75 = ระบบจะไม่ตัดสิน)

---

# ส่วนที่ 9: แก้ปัญหา

## A. Dashboard ขึ้น "⏳ กำลังรอข้อมูล" ไม่หยุด

ไล่ตามลำดับ:

1. Serial Monitor ขึ้น `🚀 [OK]` ไหม? → **ไม่ขึ้น** = ปัญหาที่บอร์ด ดูข้อ C
2. Firebase Console มีคีย์ใหม่เข้ามาไหม? → **ไม่มี** = ดูข้อ D
3. `FIREBASE_DOMAIN` ใน `secrets.toml` **ตรงกับ** `FIREBASE_HOST` ใน `secrets.h` เป๊ะไหม?
   → นี่คือสาเหตุอันดับ 1
4. `DB_PATH` ตรงกันไหม? เฟิร์มแวร์ใช้ `"/History3F"` (มี `/`) dashboard ใช้ `"History3F"` (ไม่มี `/`) — **ถูกแล้ว** อย่าไปแก้
5. กด **🔍 ตรวจ heartbeat ของบอร์ด** ใน sidebar

## B. ขึ้น 401 Unauthorized

- `FIREBASE_TOKEN` ผิด หรือคัดลอกมาไม่ครบ (มีช่องว่างหัวท้าย)
- ถ้าเพิ่งสร้าง secret ใหม่ อันเก่าจะใช้ไม่ได้ทันที ต้องแก้ทั้งสองฝั่ง
- ตรวจ Rules ว่าเป็นตามขั้น 1.4

## C. Serial Monitor ไม่ขึ้นอะไรเลย

| อาการ | สาเหตุ | แก้ |
|---|---|---|
| ว่างเปล่า | USB CDC ปิดอยู่ | Tools → USB CDC On Boot → **Enabled** แล้วแฟลชใหม่ |
| ตัวอักษรมั่ว | baud ผิด | ตั้ง 115200 |
| ค้างที่ "เชื่อมต่อ WiFi..." | 5GHz / captive portal / รหัสผิด | ใช้ hotspot มือถือ 2.4 GHz |
| `❌ NTP ล้มเหลว` | เครือข่ายบล็อก UDP port 123 | เปลี่ยนเครือข่าย หรือแก้ `NTP_SERVER1` ใน `config.h` |
| `❌ ไม่พบอุปกรณ์` บางช่อง | สายหลุด/MPU เสีย | ตรวจสายช่องนั้น |

## D. Serial ขึ้น [OK] แต่ Firebase ไม่มีข้อมูลใหม่

**เปิด `History3F_meta/heartbeat` ดู `server_ts`:**

| server_ts | แปลว่า | แก้ |
|---|---|---|
| ขยับทุก 5 วิ | บอร์ดส่งถึงจริง | ปัญหาอยู่ที่ query ฝั่ง dashboard → ข้อ A |
| ไม่ขยับ | SDK รายงานสำเร็จปลอม | ดูข้างล่าง |
| ไม่มี node นี้เลย | ยังใช้เฟิร์มแวร์เก่า | แฟลชเวอร์ชันใหม่ |

**ถ้า server_ts ไม่ขยับ:**
1. ตรวจโควตา: Firebase Console → Usage → ถ้า Downloads ใกล้ 10 GB คือชนโควตา
   (เวอร์ชันนี้ใช้ incremental fetch แล้ว ไม่ควรเกิดขึ้น — ถ้าเกิด แปลว่ายังรัน app.py เวอร์ชันเก่าอยู่)
2. ตรวจ `rssi` ใน Serial — ถ้า < -80 ให้ย้ายบอร์ดเข้าใกล้เราเตอร์
3. ตรวจ `heap` — ถ้าลดลงเรื่อย ๆ จนต่ำกว่า 30000 คือ memory leak (บอร์ดจะ restart เอง)

## E. ข้อมูลเก่าไม่ถูกลบ ฐานข้อมูลโตเรื่อย ๆ

- Serial ต้องขึ้น `🗑️ cleanup N keys` ทุก ~15 วินาที ถ้าไม่ขึ้นเลย:
  - ตรวจ `ENABLE_AUTO_CLEANUP` ใน `config.h` เป็น `true`
  - ถ้าขึ้น `⚠️ cleanup fail` ให้ดู httpCode ที่แสดง
- ถ้าใน DB มีคีย์เลขน้อย (หลักพัน/หลักล้าน) ปนกับคีย์ 13 หลัก
  → นั่นคือข้อมูลขยะจากเฟิร์มแวร์เวอร์ชันเก่า **ลบทิ้งด้วยมือ**
  (Firebase Console → คลิกจุดสามจุดข้าง `History3F` → Delete)

## F. ค่า fn กระโดดไปมา / หาพีคไม่เจอ

| อาการ | สาเหตุ | แก้ |
|---|---|---|
| RMS ต่ำ ขึ้น "แรงกระตุ้นต่ำ" | เคาะเบาไป | เคาะแรงขึ้น หรือลด `rms_min` ใน sidebar |
| fn เท่ากันทั้ง 3 ชั้นเป๊ะ | กำลังใช้ sine → นั่นคือความถี่ลำโพง | เปลี่ยนไปเคาะกระแทก |
| fn กระโดด ±2 Hz | สัญญาณรบกวนสูง / ตึกไม่นิ่ง | เพิ่ม `HISTORY_SIZE` ใน `config.py` |
| fn ติดเพดานเสมอ | fn จริงสูงกว่า Nyquist | เพิ่ม `SAMPLE_HZ` ใน `config.h` เป็น 100 |
| coherence < 0.75 ตลอด | ชั้นบนกับชั้นล่างไม่สัมพันธ์กัน | ตรวจว่าติด MPU แกน X ทิศเดียวกันครบทุกตัว |

## G. Streamlit Cloud deploy ไม่ผ่าน

| Error | แก้ |
|---|---|
| `ModuleNotFoundError: No module named 'config'` | Main file path ต้องเป็น `dashboard/app.py` |
| `KeyError: 'FIREBASE_DOMAIN'` | ยังไม่ได้วาง secrets ใน Advanced settings |
| แอปหลับ | เข้าไปเปิดสักครั้งก่อนวันนำเสนอ |

---

# ภาคผนวก: จะแก้อะไร ต้องไปไฟล์ไหน

| อยากเปลี่ยน | ไฟล์ | ตัวแปร |
|---|---|---|
| อัตราสุ่มตัวอย่าง | `firmware/.../config.h` | `SAMPLE_HZ` |
| ขา I2C | `firmware/.../config.h` | `I2C_SDA`, `I2C_SCL` |
| ช่อง TCA ของแต่ละชั้น | `firmware/.../config.h` | `CH_FLOOR1/2/3` |
| เก็บข้อมูลย้อนหลังกี่วินาที | `firmware/.../config.h` | `KEEP_SECONDS` |
| ขนาด batch ที่ส่ง | `firmware/.../config.h` | `BATCH_SIZE` |
| WiFi / Firebase | `firmware/.../secrets.h` | ทั้งหมด |
| ความถี่ refresh หน้าจอ | `dashboard/config.py` | `REFRESH_MS` |
| ย่านค้นหาความถี่ | `dashboard/config.py` | `SEARCH_LO`, `SEARCH_HI` |
| ความละเอียดสเปกตรัม | `dashboard/config.py` | `NPERSEG` |
| ความไวของ median filter | `dashboard/config.py` | `HISTORY_SIZE` |
| ต้องเข้าเงื่อนไขกี่รอบถึงเปลี่ยนสถานะ | `dashboard/config.py` | `MIN_CONSEC` |
| เกณฑ์ coherence | `dashboard/config.py` | `COH_MIN` |
| ชื่อชั้น | `dashboard/config.py` | `FLOOR_NAMES` |
| เกณฑ์สี 🟢🟡🔴 | sidebar ในแอป | ปรับสด ๆ ได้ |
| สูตร Health | `dashboard/core/damage.py` | `health_from_fn()` |
| ตรรกะเปลี่ยนสถานะ | `dashboard/core/damage.py` | `next_status()` |
| อัลกอริทึม DSP | `dashboard/core/dsp.py` | ทั้งไฟล์ |
| เงื่อนไข/ข้อความแจ้งเตือน | `dashboard/services/telegram.py` | ค่าคงที่บนสุด |
| คำสั่งที่ให้ AI | `dashboard/services/ai_assistant.py` | `SYSTEM_PROMPT` |
| หน้าตา UI | `dashboard/ui/*.py` | — |

---

# ภาคผนวก 2: การเปลี่ยนแปลงจากเวอร์ชันเดิม

## เฟิร์มแวร์

| # | เดิม | ใหม่ |
|---|---|---|
| 1 | key = `millis()` | epoch จาก NTP (13 หลัก zero-padded) |
| 2 | sampling + HTTPS ใน loop เดียว | แยก 2 task คนละคอร์ ผ่าน FreeRTOS queue |
| 3 | `delJson.set(key)` ไม่เช็คผล | raw JSON `{"key":null}` + เช็ค return + log httpCode |
| 4 | ring buffer ใน RAM หายตอน reboot | cursor เก็บใน NVS |
| 5 | key ไม่ปัด → cleanup เดาไม่ตรง | quantize เป็นทวีคูณของ 20 ms |
| 6 | credential ฝังในไฟล์ | แยก `secrets.h` + `.gitignore` |
| 7 | `batchJson.clear()` ทิ้งข้อมูลเงียบ | log ทุกกรณี |
| 8 | — | เพิ่ม heartbeat node |
| 9 | — | เพิ่ม WiFi/heap watchdog + `setSleep(false)` |
| 10 | — | เพิ่ม `sensorsScan()` ไว้ debug สายหลุด |
| 11 | ไฟล์เดียว 205 บรรทัด | 6 โมดูล แยกหน้าที่ชัดเจน |

## Dashboard

| # | เดิม | ใหม่ |
|---|---|---|
| 1 | `limitToLast=450` ทุกรอบ (4.1 GB/วัน) | incremental fetch (~0.14 GB/วัน) |
| 2 | `nperseg` แปรผัน → `df` แกว่ง | คงที่ 512 |
| 3 | `sqrt(sum(psd))` ลืมคูณ df | `sqrt(∫PSD·df)` |
| 4 | `SEARCH_HI=15` เกิน Nyquist | บังคับ `≤ 0.45·fs` |
| 5 | Welch ไม่ detrend | `detrend='linear'` + `noverlap` |
| 6 | `T = amp2/amp1` | H1 estimator + coherence gate |
| 7 | credential ฝังในไฟล์ | `secrets.toml` + `.gitignore` |
| 8 | — | `tracked_peak()` ตามล่าพีคที่เลื่อน |
| 9 | — | `wideband_energy()` ตัวชี้วัดสำรอง |
| 10 | — | แจ้งเตือน Telegram (debounce 3 ชั้น) |
| 11 | — | ผู้ช่วย AI (4 provider) |
| 12 | — | ปุ่มตรวจ heartbeat |
| 13 | ไฟล์เดียว 424 บรรทัด | 13 โมดูล + 15 unit test |
