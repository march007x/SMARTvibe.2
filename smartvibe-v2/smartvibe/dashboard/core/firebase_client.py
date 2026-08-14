"""core/firebase_client.py — ดึงข้อมูลจาก Firebase Realtime Database

จุดสำคัญ: ใช้ incremental fetch ไม่ใช่ limitToLast ทุกรอบ

🐛 บั๊กเดิม: limitToLast=450 ทุก 1.5 วินาที
   450 records x ~160 bytes = 72 KB ต่อรอบ
   → 48 KB/s → 4.1 GB/วัน → ทะลุโควตาฟรี 10 GB/เดือน ใน ~2.4 วัน
   พอเกินโควตา Firebase หยุดให้บริการ = อาการ "อยู่ ๆ ก็ค้าง"

✅ วิธีใหม่: startAt คีย์สุดท้ายที่มีอยู่ → ดึงแค่ของใหม่ ~75 record/รอบ
   ประหยัด bandwidth ราว 30 เท่า
"""
import pandas as pd
import requests

import config as C


class FirebaseClient:
    def __init__(self, domain: str = C.FIREBASE_DOMAIN, token: str = C.FIREBASE_TOKEN):
        self.domain = domain
        self.token = token
        self.session = requests.Session()
        self.last_key = None
        self.last_error = None

    # ---------- helpers ----------
    def _url(self, path: str) -> str:
        return f"https://{self.domain}/{path}.json"

    def _auth(self, query: str) -> str:
        if not self.token:
            return query
        sep = "&" if query.startswith("?") else "?"
        return f"{query}{sep}auth={self.token}"

    def _get(self, url: str, query: str = ""):
        try:
            res = self.session.get(url + self._auth(query), timeout=C.HTTP_TIMEOUT)
        except requests.RequestException as e:
            self.last_error = f"เชื่อมต่อไม่ได้: {e}"
            return None
        if res.status_code == 401:
            self.last_error = "401 — token ผิด หรือ Security Rules ไม่อนุญาต"
            return None
        if res.status_code != 200:
            self.last_error = f"HTTP {res.status_code} — ตรวจ URL / token / rules"
            return None
        self.last_error = None
        return res.json()

    # ---------- API ----------
    def fetch_new(self) -> pd.DataFrame:
        """ดึงเฉพาะข้อมูลที่ยังไม่เคยเห็น คืน DataFrame ของ "ของใหม่" เท่านั้น"""
        if self.last_key is None:
            query = f'?orderBy="$key"&limitToLast={C.FIRST_FETCH}'
        else:
            # startAt เป็น inclusive → ได้คีย์เดิมกลับมา 1 ตัว เดี๋ยว dedup ทิ้ง
            query = (f'?orderBy="$key"&startAt="{self.last_key}"'
                     f'&limitToFirst={C.INCR_LIMIT}')

        data = self._get(self._url(C.DB_PATH), query)
        if not data:
            return pd.DataFrame()

        rows = {}
        for k, v in data.items():
            if isinstance(v, dict) and "uptime_ms" in v:
                rows[k] = v
            elif isinstance(v, dict):                 # เผื่อโครงสร้างซ้อนชั้น
                for sk, sv in v.items():
                    if isinstance(sv, dict) and "uptime_ms" in sv:
                        rows[sk] = sv
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame.from_dict(rows, orient="index")
        df.index.name = "key"
        df = df.reset_index()
        df["uptime_ms"] = pd.to_numeric(df["uptime_ms"], errors="coerce")
        df = df.dropna(subset=["uptime_ms"])
        if len(df):
            self.last_key = str(df["key"].max())
        return df

    def fetch_heartbeat(self):
        """อ่าน /History3F_meta/heartbeat ที่เฟิร์มแวร์เขียนไว้

        🔍 ใช้แยกแยะสาเหตุ "ข้อมูลหยุดนิ่ง":
           server_ts ไม่ขยับ → บอร์ดส่งไม่ถึงจริง (SDK รายงาน success ปลอม)
           server_ts ขยับ    → บอร์ดปกติ ปัญหาอยู่ที่ query ฝั่งนี้
        """
        return self._get(self._url(f"{C.META_PATH}/heartbeat"))
