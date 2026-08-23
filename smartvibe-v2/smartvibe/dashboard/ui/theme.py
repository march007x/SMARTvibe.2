"""ui/theme.py — สไตล์กลางของทั้งเว็บ

รวม CSS ไว้ที่เดียว เพื่อให้ทุกส่วนหน้าตาเป็นชุดเดียวกัน
เรียก inject() ครั้งเดียวใน app.py ก่อนวาดอะไรทั้งนั้น

หลักการออกแบบ:
  - โทนมืด เน้นคอนทราสต์ต่ำสำหรับพื้นหลัง คอนทราสต์สูงสำหรับตัวเลข
  - ตัวเลขทุกตัวใช้ tabular-nums → หลักไม่ขยับตอนค่าเปลี่ยน อ่านง่ายขึ้นมาก
  - ทุกแถวในการ์ดกำหนดความสูงตายตัว → หลอดของทั้ง 3 ชั้นอยู่ระดับสายตาเดียวกัน
"""
import streamlit as st

# ---------- จานสี ----------
OK      = "#34d399"   # เขียว  ปกติ
WARN    = "#fbbf24"   # เหลือง เฝ้าระวัง
DANGER  = "#f87171"   # แดง    อันตราย
ACCENT  = "#60a5fa"   # ฟ้า    ค่ากลาง ๆ ไม่มีนัยสถานะ
MUTED   = "#8b93a7"   # เทา    ป้ายกำกับ

STATUS_COLOR = {"green": OK, "yellow": WARN, "red": DANGER}
STATUS_TEXT  = {"green": "ปกติ", "yellow": "เฝ้าระวัง", "red": "อันตราย"}
STATUS_ICON  = {"green": "●", "yellow": "▲", "red": "■"}


def bar_color(status: str, has_health: bool) -> str:
    """สีของหลอด/แท่งกราฟ

    🎨 กติกา: ปกติทุกหลอดเป็น "สีฟ้า" เหมือนกันหมด
       จะเปลี่ยนสีก็ต่อเมื่อชั้นนั้นมีปัญหาจริงเท่านั้น (เหลือง = เฝ้าระวัง, แดง = อันตราย)

    🐛 ปัญหาเดิม: ชั้นที่ผ่านเกณฑ์เป็นสีเขียว ส่วนชั้นที่ยังไม่มีค่า Health เป็นสีฟ้า
       ทำให้หน้าจอมีสามสีปนกันโดยที่ไม่มีชั้นไหนผิดปกติเลย ดูแล้วสับสนว่าสีไหนแปลว่าอะไร
       ส่วนสีเขียวยังคงใช้อยู่ที่ "ป้ายสถานะ" ท้ายการ์ด ซึ่งมีตัวหนังสือกำกับชัดเจน
    """
    if not has_health or status == "green":
        return ACCENT
    return STATUS_COLOR.get(status, ACCENT)

CSS = f"""
<style>
/* ============ โครงหน้า ============ */
.block-container {{ padding-top: 2.0rem; padding-bottom: 3rem; max-width: 1320px; }}
h1 {{ font-size: 1.75rem !important; font-weight: 700 !important;
      letter-spacing: -.02em; margin-bottom: .2rem !important; }}

.sv-h {{ font-size: 1.05rem; font-weight: 650; letter-spacing:-.01em;
         margin: 4px 0 14px; color: #e8ecf4; }}

hr {{ margin: 1.6rem 0 !important; border-color: rgba(255,255,255,.07) !important; }}

/* ============ การ์ดรายชั้น ============ */
.sv-card {{
  background: linear-gradient(180deg, rgba(255,255,255,.045), rgba(255,255,255,.015));
  border: 1px solid rgba(255,255,255,.09);
  border-radius: 16px;
  padding: 18px 18px 16px;
}}
.sv-card-top {{
  display:flex; align-items:baseline; justify-content:space-between;
  height: 30px; margin-bottom: 14px;
}}
.sv-floor {{ font-size: 1.15rem; font-weight: 700; color:#f1f4f9; letter-spacing:-.01em; }}
.sv-rms {{
  font-size: 11px; color:{MUTED}; font-variant-numeric: tabular-nums;
  background: rgba(255,255,255,.05); border-radius: 6px; padding: 3px 8px;
}}

/* --- แถวค่าหนึ่งแถว: ป้าย / ตัวเลข / คำอธิบาย / หลอด --- */
.sv-label {{
  font-size: 11px; font-weight: 600; letter-spacing:.05em;
  color:{MUTED}; height: 15px; line-height:15px; margin-bottom: 3px;
}}
.sv-value {{
  font-size: 27px; font-weight: 640; line-height: 32px; height: 32px;
  color: #f5f7fa; font-variant-numeric: tabular-nums; letter-spacing:-.02em;
}}
.sv-value.sm {{ font-size: 19px; }}
.sv-sub {{
  font-size: 11.5px; color:#7c8598; height: 17px; line-height:17px;
  font-variant-numeric: tabular-nums;
}}
.sv-track {{
  height: 7px; border-radius: 99px; background: rgba(255,255,255,.075);
  margin: 9px 0 16px; overflow:hidden;
}}
.sv-fill {{ height:100%; border-radius:99px; transition: width .35s ease; }}
.sv-track.empty {{ background: transparent; }}

/* --- ป้ายสถานะท้ายการ์ด --- */
.sv-pill {{
  display:flex; align-items:center; justify-content:center; gap:8px;
  height: 40px; border-radius: 11px; font-size: 13.5px; font-weight: 650;
  letter-spacing:-.01em;
}}
.sv-pill small {{ font-weight:500; opacity:.72; font-size:11.5px; }}

/* ============ แถบแจ้งสถานะ ============ */
.sv-banner {{
  display:flex; align-items:center; gap:10px;
  padding: 13px 16px; border-radius: 12px; font-size:14px; font-weight:600;
  border:1px solid; margin: 2px 0 6px;
}}
.sv-banner .ic {{ font-size:15px; }}

/* ============ แท่งเทียบแอมพลิจูด ============ */
.sv-amp-row {{ display:flex; align-items:center; gap:14px; margin-bottom:11px; }}
.sv-amp-name {{ width: 58px; font-size:13px; color:#c3cad8; font-weight:600; flex:none; }}
.sv-amp-track {{
  flex:1; height: 26px; border-radius: 8px;
  background: rgba(255,255,255,.05); overflow:hidden;
}}
.sv-amp-fill {{ height:100%; border-radius:8px; transition:width .35s ease; }}
.sv-amp-val {{
  width: 74px; text-align:right; font-size:13.5px; font-weight:650;
  font-variant-numeric: tabular-nums; color:#e6eaf2; flex:none;
}}

/* ============ คำอธิบายสี ============ */
.sv-legend {{ display:flex; gap:18px; margin:2px 0 4px; }}
.sv-key {{ display:flex; align-items:center; gap:7px; font-size:12px; color:{MUTED}; }}
.sv-key i {{ width:13px; height:6px; border-radius:3px; display:inline-block; }}

/* ============ แผง debug ============ */
.sv-dbg {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(196px,1fr)); gap:10px; }}
.sv-dbg-item {{
  background: rgba(255,255,255,.035); border:1px solid rgba(255,255,255,.07);
  border-radius: 10px; padding: 10px 13px;
}}
.sv-dbg-k {{ font-size:10.5px; letter-spacing:.05em; color:{MUTED}; margin-bottom:3px; }}
.sv-dbg-v {{ font-size:15px; font-weight:640; color:#eaeef6;
             font-variant-numeric: tabular-nums; word-break: break-all; }}
.sv-dbg-v.ok  {{ color:{OK}; }}
.sv-dbg-v.bad {{ color:{DANGER}; }}
.sv-dbg-url {{
  font-size:11.5px; color:#7c8598; margin-top:12px; word-break:break-all;
  font-family: ui-monospace, monospace;
}}

/* ============ ปุ่ม ============ */
/* ปุ่มล้างค่า — ให้เห็นชัดว่าเป็นการกระทำที่ต้องระวัง */
.st-key-btn_reset button {{
  border: 1px solid rgba(248,113,113,.5) !important;
  color: #fca5a5 !important; font-weight: 650 !important;
  background: rgba(248,113,113,.07) !important;
}}
.st-key-btn_reset button:hover {{
  border-color: {DANGER} !important; color: #fee2e2 !important;
  background: rgba(248,113,113,.18) !important;
}}
/* ปุ่ม AI — ใหญ่ กดง่าย */
.st-key-btn_ai_now button, .st-key-btn_ai_trend button {{
  height: 56px !important; font-size: 15.5px !important; font-weight: 650 !important;
  border-radius: 13px !important;
}}
.st-key-btn_lock button {{ height: 46px !important; font-weight: 650 !important;
                           border-radius: 11px !important; }}
.st-key-btn_reset button {{ height: 46px !important; border-radius: 11px !important; }}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def banner(level: str, text: str):
    """แถบแจ้งสถานะสีสวย ใช้แทน st.success/st.warning ที่สีจัดเกินไป"""
    palette = {
        "success": (OK,     "rgba(52,211,153,.10)", "rgba(52,211,153,.35)", "✓"),
        "warning": (WARN,   "rgba(251,191,36,.10)", "rgba(251,191,36,.35)", "!"),
        "error":   (DANGER, "rgba(248,113,113,.10)","rgba(248,113,113,.38)","×"),
        "info":    (ACCENT, "rgba(96,165,250,.10)", "rgba(96,165,250,.32)", "i"),
    }
    c, bg, bd, ic = palette.get(level, palette["info"])
    st.markdown(
        f'<div class="sv-banner" style="color:{c};background:{bg};border-color:{bd}">'
        f'<span class="ic">{ic}</span><span>{text}</span></div>',
        unsafe_allow_html=True)


def bar(pct: float, color: str) -> str:
    """คืน HTML ของหลอดแสดงค่า (pct 0-100)"""
    p = max(0.0, min(100.0, float(pct)))
    return (f'<div class="sv-track"><div class="sv-fill" '
            f'style="width:{p:.1f}%;background:{color}"></div></div>')
