"""app.py — จุดเริ่มต้นของ dashboard

ไฟล์นี้ทำหน้าที่ "ประกอบร่าง" อย่างเดียว ตรรกะจริงอยู่ในโมดูล:
  config.py            ค่าตั้งต้นทั้งหมด
  core/firebase_client แดึงข้อมูล (incremental fetch)
  core/buffer          บัฟเฟอร์ rolling ฝั่ง client
  core/dsp             ประมวลผลสัญญาณ (pure, เทสต์ได้)
  core/damage          ตรรกะ Health + เครื่องสถานะ (pure, เทสต์ได้)
  core/analysis        ท่อประมวลผลหลัก
  core/state           จัดการ session_state
  services/telegram    แจ้งเตือน
  services/ai_assistant ผู้ช่วย AI
  ui/*                 ส่วนแสดงผล

รัน: streamlit run app.py
"""
import json
import time

import streamlit as st
from streamlit_autorefresh import st_autorefresh

import config as C
from core import state
from core.analysis import analyze
from core.buffer import RollingBuffer
from core.firebase_client import FirebaseClient
from services import ai_assistant, telegram
from ui import charts, debug, floors, sidebar
from ui import theme

st.set_page_config(page_title="SmartVibe", layout="wide")
theme.inject()
st.title("SmartVibe — เฝ้าระวังโครงสร้างอาคารจากการสั่นสะเทือน")

ss = st.session_state
state.init(ss)

# วัตถุที่ต้องอยู่ข้ามรอบ refresh
if "client" not in ss:
    ss.client = FirebaseClient()
    ss.buffer = RollingBuffer()


def main():
    t0 = time.perf_counter()

    mode, th = sidebar.render(ss.client)

    # ---------- 1) ดึงข้อมูล ----------
    df = ss.buffer.extend(ss.client.fetch_new())
    if ss.client.last_error:
        st.sidebar.error(ss.client.last_error)
    if len(df) <= 100:
        st.info("⏳ กำลังรอข้อมูลจากเซ็นเซอร์... "
                f"(ได้ {len(df)} จุด ต้องการมากกว่า 100)")
        return

    # ---------- 2) เช็คว่าข้อมูลขยับไหม ----------
    stuck = state.update_stuck(ss, df)
    telegram.on_stuck(stuck)
    if stuck >= 4:
        theme.banner("error", "ข้อมูลหยุดนิ่ง อาจเกิดปัญหาบางอย่าง")

    # ---------- 3) วิเคราะห์ ----------
    result = analyze(df, ss, mode, th)

    if result.sine_detected and result.active_mode == "fn":
        theme.banner("warning",
                     "ตรวจพบการกระตุ้นแบบไซน์ความถี่เดียว แต่โหมดปัจจุบันคือติดตาม fn "
                     "— ค่าที่เห็นคือความถี่ลำโพง ไม่ใช่ของตึก")

    # ---------- 4) ปุ่มควบคุม ----------
    c1, c2 = st.columns([2, 1], gap="medium")
    with c1:
        if st.button("🔒  ล็อก Baseline ขณะโครงสร้างสมบูรณ์",
                     type="primary", key="btn_lock", use_container_width=True):
            if state.lock_baseline(ss, result):
                st.rerun()
            else:
                theme.banner("warning",
                             "ยังล็อกไม่ได้ — สัญญาณอ่อน หาพีคไม่เจอ หรือ coherence ต่ำ")
    with c2:
        if st.button("🗑️  ล้างค่าทั้งหมด", key="btn_reset", use_container_width=True):
            state.reset_all(ss)
            st.rerun()

    st.markdown("---")

    # ---------- 5) แสดงผล ----------
    floors.render(result, ss, th)
    st.markdown("---")
    charts.amplitude_bar(result, ss)
    st.markdown("---")
    charts.spectrum(result)

    # ---------- 6) เก็บประวัติสำหรับวิเคราะห์แนวโน้ม ----------
    # เก็บทุก 30 วินาที (ไม่ใช่ทุก refresh) — ดู core/state.log_health()
    state.log_health(ss, result)

    # ---------- 7) ผู้ช่วย AI ----------
    st.markdown("---")
    st.markdown('<div class="sv-h">AI วิเคราะห์เบื้องต้น</div>', unsafe_allow_html=True)

    providers = ai_assistant.available_providers()

    # จัดทุกอย่างของส่วน AI ให้อยู่กลางจอ อ่านง่าย ไม่กวาดสายตาไปมา
    _, mid, _ = st.columns([1, 3, 1])
    with mid:
        provider = st.selectbox("ผู้ให้บริการ", providers, index=0)

        level, msg = ai_assistant.status_line(provider)
        theme.banner(level, msg)

        snap = ai_assistant.snapshot(result, ss)
        n_log = len(ss.get("health_log", []))
        ready = ai_assistant.is_ready(provider)

        b1, b2 = st.columns(2, gap="medium")
        with b1:
            # ✅ on-demand เท่านั้น ไม่ผูกกับ auto-refresh
            if st.button("🔍  วิเคราะห์สถานะตอนนี้", key="btn_ai_now",
                         use_container_width=True, disabled=not ready):
                with st.spinner("กำลังวิเคราะห์..."):
                    ss.ai_result = ai_assistant.analyze_cached(
                        provider, ai_assistant.hash_of(snap), snap)
        with b2:
            if st.button(f"📈  วิเคราะห์แนวโน้ม ({n_log} จุด)", key="btn_ai_trend",
                         use_container_width=True, disabled=not ready):
                with st.spinner("กำลังประเมินแนวโน้ม..."):
                    hist_json = json.dumps(ss["health_log"], ensure_ascii=False)
                    ss.ai_trend = ai_assistant.analyze_trend_cached(
                        provider, ai_assistant.hash_of(hist_json), hist_json)

        if ss.get("ai_result"):
            st.info("**สถานะตอนนี้**\n\n" + ss.ai_result)
        if ss.get("ai_trend"):
            st.warning("**แนวโน้ม**\n\n" + ss.ai_trend)

    st.markdown("---")
    debug.render(result, df, t0, ss.client, stuck)


try:
    main()
except Exception as e:
    # 🐛 บั๊กเดิม: st.exception(Exception) ส่ง "คลาส" ไม่ใช่ตัว error จริง
    #    ทำให้เวลาแอปพัง หน้าเว็บไม่บอกสาเหตุเลย ไล่จับปัญหาไม่ได้
    st.error(f"เกิดข้อผิดพลาดระหว่างประมวลผล: {type(e).__name__}: {e}")
    st.exception(e)
    # ไม่ raise ซ้ำ เพื่อให้ st_autorefresh ด้านล่างยังทำงาน
    # → หน้าเว็บพยายามใหม่เองในรอบถัดไป ไม่ค้างตายถาวร

st_autorefresh(interval=C.REFRESH_MS, limit=None, key="smartvibe_autorefresh")
