"""ui/floors.py — การ์ดแสดงผลรายชั้น

ออกแบบให้ทั้ง 3 การ์ดมี "จำนวนแถวเท่ากันเสมอ" และแต่ละแถวสูงคงที่
→ หลอดแสดงค่าของทุกชั้นอยู่ระดับสายตาเดียวกัน เปรียบเทียบด้วยตาได้ทันที
ช่องไหนไม่มีข้อมูลจะแสดง "—" แทนที่จะหายไป เพื่อไม่ให้ความสูงเลื่อน
"""
import streamlit as st

import config as C
from core.damage import next_status
from services import telegram
from ui import theme as T


def _row(label: str, value: str, sub: str = "&nbsp;",
         pct=None, color: str = T.ACCENT, small: bool = False) -> str:
    """หนึ่งแถวของการ์ด: ป้าย → ตัวเลข → คำอธิบาย → หลอด (ถ้ามี)"""
    cls = "sv-value sm" if small else "sv-value"
    html = (f'<div class="sv-label">{label}</div>'
            f'<div class="{cls}">{value}</div>'
            f'<div class="sv-sub">{sub}</div>')
    # ไม่มีค่า → เว้นที่ว่างเปล่า ๆ แทนหลอด เพื่อให้แถวถัดไปยังตรงกันทุกชั้น
    html += T.bar(pct, color) if pct is not None else '<div class="sv-track empty"></div>'
    return html


def render(result, ss, th):
    amp_max = max([f.amp for f in result.floors if f.amp], default=0.0)
    cols = st.columns(C.N_FLOORS, gap="medium")

    for i, fr in enumerate(result.floors):
        # ---------- 1) ตัดสินสถานะก่อน (ต้องรู้สีก่อนวาด) ----------
        pct = fr.health
        status, cnt = ss[f"status{i}"], ss[f"consec{i}"]
        judged = False

        if pct is not None:
            if result.excitation_ok:
                status, cnt, direction = next_status(
                    ss[f"status{i}"], ss[f"consec{i}"], ss[f"consec_dir{i}"], pct, th)
                ss[f"status{i}"], ss[f"consec{i}"], ss[f"consec_dir{i}"] = status, cnt, direction
                telegram.on_status_change(i, status, pct)
                telegram.on_health_sample(i, pct)
                judged = True

        color = T.STATUS_COLOR.get(status, T.OK) if pct is not None else T.ACCENT

        # ---------- 2) แถวแอมพลิจูด ----------
        if fr.amp is not None:
            amp_val = f"{fr.amp:.4f}"
            amp_pct = (fr.amp / amp_max * 100) if amp_max > 0 else 0
            if i == 0:
                amp_sub = "ชั้นอ้างอิงสำหรับเทียบสัดส่วน"
            elif result.floors[0].amp:
                amp_sub = f"× {fr.amp / result.floors[0].amp:.2f} ของชั้น 1"
            else:
                amp_sub = "&nbsp;"
        else:
            amp_val, amp_pct, amp_sub = "—", 0, "ยังไม่มีข้อมูล"

        # ---------- 3) แถวตัวชี้วัดหลัก ----------
        if fr.fn is None:
            m_label, m_value, m_sub, m_small = "สัญญาณ", "—", "หาพีคไม่เจอ / ไม่มีข้อมูลช่องนี้", True
        elif result.active_mode == "fn":
            base = ss.get(f"base_fn{i}")
            m_label, m_small = "ความถี่ธรรมชาติ fn", False
            m_value = f"{fr.fn:.2f} Hz"
            m_sub = (f"เทียบ baseline {fr.fn - base:+.2f} Hz" if base
                     else "ยังไม่ได้ล็อก baseline")
        elif i == 0:
            m_label, m_value, m_small = "บทบาทของชั้นนี้", "ชั้นอ้างอิง", True
            m_sub = "ใช้เป็นตัวหารของ Transmissibility"
        else:
            T_now = result.T21 if i == 1 else result.T32
            T_base = ss.get("base_T21") if i == 1 else ss.get("base_T32")
            coh = result.coh21 if i == 1 else result.coh32
            m_label = f"Transmissibility ชั้น{i+1}/ชั้น{i}"
            m_small = False
            if T_now is not None:
                m_value = f"{T_now:.3f}"
                m_sub = (f"เทียบ baseline {T_now - T_base:+.3f} · coherence {coh:.2f}"
                         if T_base else f"coherence {coh:.2f}")
            else:
                m_value, m_small = "—", True
                m_sub = f"coherence ต่ำ ({coh:.2f}) ข้อมูลยังเชื่อไม่ได้"

        # ---------- 4) แถว Health ----------
        if pct is None:
            h_value, h_pct, h_sub = "—", None, "กดล็อก Baseline ขณะโครงสร้างสมบูรณ์"
        else:
            h_value, h_pct = f"{pct:.1f}%", pct
            h_sub = (f"ยืนยัน {cnt}/{C.MIN_CONSEC} รอบ" if judged and cnt
                     else ("แรงกระตุ้นต่ำ — คงสถานะเดิม" if not result.excitation_ok
                           else "&nbsp;"))

        # ---------- 5) ป้ายสถานะ ----------
        if pct is None:
            pill = ('<div class="sv-pill" style="color:#8b93a7;'
                    'background:rgba(255,255,255,.045)">รอล็อก Baseline</div>')
        else:
            sc = T.STATUS_COLOR[status]
            note = "" if result.excitation_ok else " <small>· พักการตัดสิน</small>"
            pill = (f'<div class="sv-pill" style="color:{sc};'
                    f'background:{sc}1a;border:1px solid {sc}44">'
                    f'{T.STATUS_ICON[status]} {T.STATUS_TEXT[status]}{note}</div>')

        # ---------- 6) ประกอบการ์ด ----------
        with cols[i]:
            st.markdown(
                '<div class="sv-card">'
                f'<div class="sv-card-top"><span class="sv-floor">ชั้น {i+1}</span>'
                f'<span class="sv-rms">RMS {fr.rms:.4f}</span></div>'
                + _row("แอมพลิจูดการแกว่ง", amp_val, amp_sub, amp_pct, color)
                + _row(m_label, m_value, m_sub, None, color, m_small)
                + _row("HEALTH เทียบ BASELINE", h_value, h_sub, h_pct, color)
                + pill +
                '</div>',
                unsafe_allow_html=True)
