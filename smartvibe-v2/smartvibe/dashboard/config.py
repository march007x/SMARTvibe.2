"""config.py — ค่าตั้งต้นทั้งหมดของ dashboard

แก้ค่าการทำงานที่ไฟล์นี้ที่เดียว ส่วนความลับ (token) อยู่ใน
.streamlit/secrets.toml ซึ่งไม่ถูก push ขึ้น GitHub
"""
import os
from dataclasses import dataclass
from functools import lru_cache

import streamlit as st

# ---------- ตัวอ่าน secrets ที่ทนทางรันทุกแบบ ----------
# 🐛 บั๊กเดิม: Streamlit หา .streamlit/secrets.toml จาก "โฟลเดอร์ที่สั่งรัน" (CWD)
#    ไฟล์จริงอยู่ที่ dashboard/.streamlit/ → ถ้าสั่ง
#        streamlit run dashboard/app.py     (จาก root ของ repo)
#    จะหา secrets ไม่เจอ แล้วขึ้น "ยังไม่ได้ตั้ง FIREBASE_DOMAIN" ทั้งที่กรอกแล้ว
# ✅ แก้: ถ้า st.secrets ไม่มีคีย์นั้น ให้ไปอ่านไฟล์ข้าง ๆ config.py เองอีกชั้น
_LOCAL_SECRETS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              ".streamlit", "secrets.toml")


@lru_cache(maxsize=1)
def _local_secrets() -> dict:
    """อ่าน dashboard/.streamlit/secrets.toml ตรง ๆ (สำรองเวลา CWD ไม่ตรง)"""
    if not os.path.exists(_LOCAL_SECRETS):
        return {}
    try:
        try:
            import tomllib                       # Python 3.11+
        except ImportError:
            import tomli as tomllib              # Python 3.10 ต้อง pip install tomli
        with open(_LOCAL_SECRETS, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _secret(key: str, default: str = "") -> str:
    """อ่าน secrets แบบไม่พังถ้ายังไม่มีไฟล์ secrets.toml

    ลำดับการค้นหา:
      1. st.secrets           (Streamlit Cloud → Settings → Secrets, หรือ CWD ตรง)
      2. ไฟล์ dashboard/.streamlit/secrets.toml  (เวลารันจาก root ของ repo)
      3. environment variable (เผื่อ deploy แบบอื่น เช่น Docker)
      4. ค่า default

    ⚠️ st.secrets.get() จะ raise ถ้าไม่มีไฟล์เลย ไม่ได้คืน default
    จึงต้องห่อ try/except ไว้
    """
    try:
        val = st.secrets.get(key, None)
        if val not in (None, ""):
            return str(val)
    except Exception:
        pass

    val = _local_secrets().get(key)
    if val not in (None, ""):
        return str(val)

    return os.environ.get(key, default)


# ---------- Firebase ----------
# ⚠️⚠️ ต้องตรงกับ FIREBASE_HOST และ DB_PATH ในเฟิร์มแวร์เป๊ะ ๆ
#      บั๊กตัวหลักของเวอร์ชันเดิมคือสองฝั่งชี้คนละฐานข้อมูลกัน
FIREBASE_DOMAIN = _secret("FIREBASE_DOMAIN", "")
FIREBASE_TOKEN  = _secret("FIREBASE_TOKEN", "")
DB_PATH   = "History3F"
META_PATH = "History3F_meta"

# ---------- การดึงข้อมูล ----------
BUFFER_SIZE   = 900    # เก็บใน RAM ฝั่ง client (18 วินาที @ 50 Hz)
FIRST_FETCH   = 600    # ดึงครั้งแรกเท่านี้ ครั้งต่อไปดึงเฉพาะของใหม่
INCR_LIMIT    = 400    # เพดานต่อรอบ incremental
REFRESH_MS    = 2200   # ⚠️ ค่าต่ำสุดของคาบรีเฟรช — ต้องมากกว่าเวลาประมวลผลจริง
                       #    (วัดได้ ~1250 ms ในแผง debug) ไม่งั้นนาฬิกาของ
                       #    streamlit-autorefresh จะยิงทับตอนสคริปต์ยังทำงานไม่เสร็จ
                       #    แล้วตัดงานทิ้งกลางคัน — ดูคำอธิบายเต็มใน app.py
HTTP_TIMEOUT  = 3.0

# ---------- DSP ----------
NPERSEG    = 512    # ⚠️ ต้องคงที่! ถ้าแปรผันตามจำนวนจุด df จะแกว่ง
                    #    ทำให้แอมพลิจูดกระโดดเองโดยโครงสร้างไม่ได้เปลี่ยน
NOMINAL_FS = 50.0
SEARCH_LO  = 2.0
SEARCH_HI  = 24.0   # จะถูกบังคับไม่ให้เกิน 0.45*fs อีกชั้นใน dsp.py
TRACK_HALF = 2.0    # หน้าต่างตามล่าพีค ±Hz
COH_MIN    = 0.75   # coherence ต่ำกว่านี้ = ข้อมูลไม่น่าเชื่อ

# ---------- ตรรกะสถานะ ----------
HISTORY_SIZE = 7    # median filter กี่จุด
MIN_CONSEC   = 3    # ต้องเข้าเงื่อนไขติดกันกี่รอบถึงเปลี่ยนสถานะ
SINE_SHARP   = 40   # sharpness เกินนี้ = น่าจะเป็น sine ความถี่เดียว

FLOOR_NAMES = ["ชั้น 1", "ชั้น 2", "ชั้น 3"]
N_FLOORS = 3

# ---------- ประวัติสำหรับ AI วิเคราะห์แนวโน้ม ----------
TREND_SAMPLE_SEC = 30    # เก็บ health ลง log ทุกกี่วินาที (ไม่ใช่ทุก refresh!)
TREND_MAX_POINTS = 240   # เก็บย้อนหลังกี่จุด (240 x 30 วิ = 2 ชั่วโมง)


@dataclass
class Thresholds:
    """เกณฑ์เปลี่ยนสถานะ — ผู้ใช้ปรับได้จาก sidebar"""
    g2y: float = 90.0   # 🟢→🟡 เมื่อ Health ต่ำกว่า
    y2r: float = 70.0   # 🟡→🔴
    y2g: float = 94.0   # 🟡→🟢 (ขาฟื้น)
    r2y: float = 75.0   # 🔴→🟡 (ขาฟื้น)
    rms_min: float = 0.010   # RMS ขั้นต่ำที่ถือว่ามีแรงกระตุ้นพอ
