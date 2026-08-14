"""ui/charts.py — กราฟเทียบแอมพลิจูด และกราฟสเปกตรัม"""
import pandas as pd
import streamlit as st

import config as C
from ui import theme as T


def amplitude_bar(result, ss):
    """แท่งเทียบแอมพลิจูดแต่ละชั้น

    สีของแท่งผูกกับสถานะของชั้นนั้น:
      เขียว = ปกติ · เหลือง = เฝ้าระวัง · แดง = อันตราย
    ทำให้เห็นได้ทันทีว่าชั้นที่แกว่งผิดปกติคือชั้นไหน โดยไม่ต้องเลื่อนขึ้นไปดูการ์ด
    """
    amps = [f.amp for f in result.floors]
    if not any(a is not None for a in amps):
        return

    st.markdown('<div class="sv-h">แอมพลิจูดการแกว่งแต่ละชั้น</div>',
                unsafe_allow_html=True)

    mx = max([a for a in amps if a], default=0.0) or 1.0
    rows = ""
    for i, a in enumerate(amps):
        status = ss.get(f"status{i}", "green")
        has_health = result.floors[i].health is not None
        color = T.STATUS_COLOR.get(status, T.OK) if has_health else T.ACCENT
        pct = (a / mx * 100) if a else 0.0
        val = f"{a:.4f}" if a else "—"
        rows += (
            f'<div class="sv-amp-row">'
            f'<div class="sv-amp-name">ชั้น {i+1}</div>'
            f'<div class="sv-amp-track"><div class="sv-amp-fill" '
            f'style="width:{pct:.1f}%;background:{color}"></div></div>'
            f'<div class="sv-amp-val" style="color:{color}">{val}</div>'
            f'</div>')
    st.markdown(rows, unsafe_allow_html=True)

    st.caption("ปกติชั้นบนจะแกว่งแรงกว่าชั้นล่าง — แท่งเปลี่ยนเป็นสีเหลือง/แดง "
               "เมื่อชั้นนั้นเข้าเกณฑ์เฝ้าระวังหรืออันตราย")


def spectrum(result):
    if result.freqs is None or any(f.psd is None for f in result.floors):
        return

    st.markdown('<div class="sv-h">กราฟสเปกตรัม (PSD) แยกตามชั้น</div>',
                unsafe_allow_html=True)

    valid = result.freqs >= 0.5
    df = pd.DataFrame(
        {C.FLOOR_NAMES[i]: result.floors[i].psd[valid] for i in range(C.N_FLOORS)},
        index=result.freqs[valid])
    nyq = result.fs * 0.5
    st.line_chart(df[df.index <= nyq], x_label="Frequency (Hz)", y_label="PSD (g²/Hz)")
    st.caption("จุดที่ล็อค Baseline จะเป็นจุดพีคที่กราฟพุ่งขึ้นสูงที่สุด")
