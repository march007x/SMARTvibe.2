"""ui/sidebar.py — แถบตั้งค่าด้านซ้าย"""
import streamlit as st

import config as C
from config import Thresholds
from services import telegram


def render(client):
    st.sidebar.header("⚙️ การตั้งค่า")
    st.sidebar.caption(f"📡 DB: `{C.FIREBASE_DOMAIN.split('.')[0] or '—ยังไม่ตั้งค่า—'}`")
    st.sidebar.caption(f"📂 path: `/{C.DB_PATH}`")

    if not C.FIREBASE_DOMAIN:
        st.sidebar.error("ยังไม่ได้ตั้ง FIREBASE_DOMAIN ใน .streamlit/secrets.toml")

    st.sidebar.markdown("---")
    mode = st.sidebar.radio(
        "โหมดการวิเคราะห์",
        ["อัตโนมัติ (แนะนำ)",
         "ติดตาม fn (White Noise/Sweep/เคาะ)",
         "ไซน์คงที่ (Transmissibility)"], index=0)

    st.sidebar.caption("โหมด fn: Health = (fn/fn₀)² x 100 = % ของ stiffness ที่เหลือ")
    st.sidebar.caption("โหมดไซน์: Health = ความคล้ายของ Transmissibility เทียบ baseline")
    st.sidebar.info("💡 แนะนำที่สุด: **เคาะกระแทก** แล้วใช้โหมดติดตาม fn "
                    "— ไม่ต้องใช้ลำโพง วัดซ้ำได้ และเห็น fn จริงของตึก")

    st.sidebar.markdown("---")
    th = Thresholds(
        g2y=st.sidebar.slider("🟢→🟡 (Health < กี่ %)", 70, 99, 90, 1),
        y2r=st.sidebar.slider("🟡→🔴 (Health < กี่ %)", 40, 95, 70, 1),
        y2g=st.sidebar.slider("🟡→🟢 (ขาฟื้น ≥ กี่ %)", 70, 100, 94, 1),
        r2y=st.sidebar.slider("🔴→🟡 (ขาฟื้น ≥ กี่ %)", 45, 99, 75, 1),
        rms_min=st.sidebar.number_input("RMS ขั้นต่ำ (ยามตรวจแรงกระตุ้น)",
                                        0.0, 1.0, 0.010, 0.005),
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔔 การแจ้งเตือน")
    if telegram.enabled():
        st.sidebar.success("Telegram พร้อมใช้งาน")
        if st.sidebar.button("ส่งข้อความทดสอบ"):
            st.sidebar.success("ส่งแล้ว") if telegram.test() else st.sidebar.error("ล้มเหลว")
    else:
        st.sidebar.caption("ยังไม่ตั้ง TELEGRAM_TOKEN / TELEGRAM_CHAT_ID")

    st.sidebar.markdown("---")
    if st.sidebar.button("🔍 ตรวจ heartbeat ของบอร์ด"):
        hb = client.fetch_heartbeat()
        if hb:
            st.sidebar.json(hb)
        else:
            st.sidebar.error(client.last_error or "ไม่พบ heartbeat — บอร์ดยังไม่ได้แฟลชเวอร์ชันใหม่?")

    return mode, th
