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
from core import rules, state
from core.analysis import analyze
from core.buffer import RollingBuffer
from core.firebase_client import FirebaseClient
from services import ai_assistant, telegram
from ui import charts, debug, floors, insight, sidebar
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


def run_ai_job() -> bool:
    """ทำงาน AI ที่ค้างคิวอยู่ — ต้องทำ "ก่อน" อย่างอื่นทั้งหมดในสคริปต์

    🐛 บั๊กที่แก้: กดปุ่ม AI แล้วไม่มีอะไรขึ้นเลย
    ------------------------------------------------------------------
    ต้นเหตุอยู่ในตัว streamlit-autorefresh เอง โค้ดฝั่งเบราว์เซอร์ของมันคือ

        window.setInterval(() => Streamlit.setComponentValue(n), interval)

    สังเกตว่าเป็น **setInterval (ยิงซ้ำ)** ไม่ใช่ setTimeout (ยิงครั้งเดียว)
    และมันจะถูก clear ก็ต่อเมื่อสคริปต์ฝั่ง Python วาดหน้าเสร็จรอบใหม่เท่านั้น
    แปลว่า "ระหว่างที่ Python ยังทำงานอยู่ นาฬิกาตัวนี้ก็ยังเดินและยิงซ้ำได้"

    ทีนี้ Streamlit มีกติกาว่า ถ้ามีคำขอ rerun ค้างอยู่ พอสคริปต์เรียกคำสั่ง
    st.* ตัวถัดไป (ซึ่งต้องส่งข้อมูลไปวาดหน้า) มันจะโยน RerunException ทิ้ง
    งานที่ทำค้างอยู่ทันที

    ลำดับเหตุการณ์ของเดิมจึงเป็นแบบนี้ทุกครั้ง:
        t=0 ms      เริ่มรอบใหม่
        t≈1245 ms   วิเคราะห์สัญญาณเสร็จ (ค่าที่วัดได้จริงในแผง debug)
        t≈1300 ms   ไหลมาถึงปุ่ม AI → ปุ่มคืน True → เข้า with st.spinner(...)
        t=1500 ms   ⏰ setInterval ยิง → มีคำขอ rerun ค้าง
        →           st.spinner ต้องส่งข้อมูลไปวาดหน้า → RerunException เด้ง
                    → **ยังไม่ทันได้เรียก Groq เลยด้วยซ้ำ** ss.ai_result จึงว่างตลอด
        →           รอบใหม่เริ่ม ปุ่มกลับเป็น False → เหมือนไม่เคยกด

    ✅ วิธีแก้: แยก "กดปุ่ม" ออกจาก "เรียก AI" คนละรอบ
       - ตอนกดปุ่ม: แค่จดคิวลง session_state (เป็น Python ล้วน ไม่ส่งอะไรไปวาดหน้า
         จึงไม่มีทางโดน RerunException ตัด) แล้วปล่อยให้รอบนั้นจบไป
       - รอบถัดไป: ฟังก์ชันนี้ทำงานตั้งแต่ต้นสคริปต์ ตอนที่ยังไม่มีคำขอ rerun ค้าง
         และตลอดช่วงที่รอ Groq ตอบก็ไม่เรียก st.* เลยสักคำสั่ง → ตัดไม่ได้
    """
    job = ss.pop("ai_job", None)
    if not job:
        return False
    kind, provider, payload = job
    slot = "ai_result" if kind == "now" else "ai_trend"
    try:
        if kind == "now":
            ss[slot] = ai_assistant.analyze_cached(
                provider, ai_assistant.hash_of(payload), payload)
        else:
            ss[slot] = ai_assistant.analyze_trend_cached(
                provider, ai_assistant.hash_of(payload), payload)
    except Exception as e:
        ss[slot] = f"⚠️ เรียก AI ไม่สำเร็จ: {type(e).__name__}: {e}"
    return True


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

    # หมายเหตุ: คำเตือนอัตโนมัติ (ฮาร์มอนิก / โหนด / coherence ต่ำ) ถูกย้ายไปไว้ใน
    # แผง debug ทั้งหมดแล้ว เพื่อไม่ให้มีแถบสีมาบังหน้าจอหลักตอนนำเสนอ

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

    # ---------- 7) สรุปผล — วางคู่กัน ซ้าย: กฎวิศวกรรม / ขวา: AI ----------
    st.markdown("---")
    col_rule, col_ai = st.columns([1.15, 1], gap="large")

    # ซ้าย: สรุปจากกฎวิศวกรรมล้วน ๆ ไม่ใช้อินเทอร์เน็ต ไม่มีโควตา
    # ทำงานได้เสมอแม้ AI ล่ม → เป็นตัวหลักที่ใช้ตัดสินใจ
    with col_rule:
        st.markdown('<div class="sv-h">วิเคราะห์ข้อมูลจากความถี่</div>',
                    unsafe_allow_html=True)
        # กันไว้: ถ้าตัวสรุปผลมีบั๊ก ให้พังอยู่ในกรอบนี้กรอบเดียว
        # ไม่ใช่ลากทั้งหน้าจอ (กราฟ/สถานะรายชั้น) ตายไปด้วย
        try:
            insight.render(rules.evaluate(result, ss, th))
        except Exception as e:
            theme.banner("error", f"สรุปผลรอบนี้ไม่สำเร็จ ({type(e).__name__}) "
                                  "ส่วนอื่นของหน้าจอยังใช้งานได้ตามปกติ")

    # ขวา: AI ภายนอก เป็นส่วนเสริมสำหรับเรียบเรียงคำอธิบาย
    with col_ai:
        st.markdown('<div class="sv-h">AI วิเคราะห์เบื้องต้น</div>',
                    unsafe_allow_html=True)
        providers = ai_assistant.available_providers()
        provider = st.selectbox("ผู้ให้บริการ", providers, index=0)

        level, msg = ai_assistant.status_line(provider)
        theme.banner(level, msg)

        snap = ai_assistant.snapshot(result, ss)
        n_log = len(ss.get("health_log", []))
        ready = ai_assistant.is_ready(provider)

        pending = ss.get("ai_job")

        b1, b2 = st.columns(2, gap="medium")
        with b1:
            # ✅ กดปุ่ม = "จดคิว" อย่างเดียว ไม่เรียก API ในรอบนี้
            #    (เหตุผลเต็ม ๆ อยู่ใน docstring ของ run_ai_job() ด้านบน)
            if st.button("🔍  วิเคราะห์สถานะตอนนี้", key="btn_ai_now",
                         use_container_width=True,
                         disabled=not ready or bool(pending)):
                ss.ai_job = ("now", provider, snap)
                pending = ss.ai_job
        with b2:
            if st.button(f"📈  วิเคราะห์แนวโน้ม ({n_log} จุด)", key="btn_ai_trend",
                         use_container_width=True,
                         disabled=not ready or bool(pending)):
                ss.ai_job = ("trend", provider,
                             json.dumps(ss["health_log"], ensure_ascii=False))
                pending = ss.ai_job

        if pending:
            theme.banner("info", "กำลังส่งคำถามให้ AI… คำตอบจะขึ้นภายในไม่กี่วินาที")

        if ss.get("ai_result"):
            st.info("**สถานะตอนนี้**\n\n" + ss.ai_result)
        if ss.get("ai_trend"):
            st.warning("**แนวโน้ม**\n\n" + ss.ai_trend)

    st.markdown("---")
    debug.render(result, df, t0, ss.client, stuck)

    # จำเวลาที่ใช้จริงรอบนี้ไว้ตั้งจังหวะ auto-refresh ให้ยาวกว่าเสมอ (ดูท้ายไฟล์)
    ss["last_elapsed_ms"] = (time.perf_counter() - t0) * 1000


# ---------- ทำงาน AI ที่ค้างคิวก่อนเป็นอันดับแรก ----------
# ต้องอยู่ "ก่อน" main() เพราะช่วงต้นสคริปต์ยังไม่มีคำขอ rerun ค้างอยู่
if run_ai_job():
    st.rerun()          # ได้คำตอบแล้ว วาดหน้าใหม่ทั้งหน้าให้เห็นผลทันที

try:
    main()
except Exception as e:
    # 🐛 บั๊กเดิม: st.exception(Exception) ส่ง "คลาส" ไม่ใช่ตัว error จริง
    #    ทำให้เวลาแอปพัง หน้าเว็บไม่บอกสาเหตุเลย ไล่จับปัญหาไม่ได้
    st.error(f"เกิดข้อผิดพลาดระหว่างประมวลผล: {type(e).__name__}: {e}")
    st.exception(e)
    # ไม่ raise ซ้ำ เพื่อให้ st_autorefresh ด้านล่างยังทำงาน
    # → หน้าเว็บพยายามใหม่เองในรอบถัดไป ไม่ค้างตายถาวร

# ---------- ตั้งจังหวะ auto-refresh แบบปรับตัวเอง ----------
# กติกา: คาบรีเฟรชต้อง "ยาวกว่าเวลาประมวลผลจริง" เสมอ
# ถ้าสั้นกว่า นาฬิกาของ streamlit-autorefresh (setInterval) จะยิงทับขณะที่
# Python ยังทำงานไม่เสร็จ → สคริปต์ถูกตัดกลางคัน → ปุ่มที่กดไว้หายไปเฉย ๆ
# (เดิมตั้งไว้ 1500 ms แต่วัดเวลาประมวลผลจริงได้ ~1245 ms เหลือระยะเผื่อแค่ 255 ms)
if ss.get("ai_job"):
    _interval = 300                      # มีคิว AI ค้าง → รีบเข้ารอบใหม่ไปทำงาน
else:
    _interval = max(C.REFRESH_MS, int(ss.get("last_elapsed_ms", 0) * 2))
st_autorefresh(interval=_interval, limit=None, key="smartvibe_autorefresh")
