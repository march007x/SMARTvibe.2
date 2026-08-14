"""ui/debug.py — แผงข้อมูลสำหรับไล่จับปัญหา

จัดเป็นตารางการ์ดย่อย อ่านเร็วกว่าข้อความยาว ๆ ต่อกัน
ค่าที่ผิดปกติจะเป็นสีแดงให้เห็นทันทีโดยไม่ต้องรู้ว่าค่าปกติควรเป็นเท่าไร
"""
import time

import numpy as np
import streamlit as st

import config as C


def _item(key: str, val: str, tone: str = "") -> str:
    return (f'<div class="sv-dbg-item"><div class="sv-dbg-k">{key}</div>'
            f'<div class="sv-dbg-v {tone}">{val}</div></div>')


def render(result, df, t0, client, stuck):
    with st.expander("ข้อมูลทางเทคนิค (debug)"):
        dts = np.diff(df["uptime_ms"].values.astype(float))
        good = dts[(dts >= 5) & (dts <= 150)]
        dt_med = np.median(good) if len(good) else float("nan")
        elapsed = (time.perf_counter() - t0) * 1000

        fn_txt = " / ".join(f"{f.fn:.2f}" if f.fn else "—" for f in result.floors)
        amp_txt = " / ".join(f"{f.amp:.4f}" if f.amp else "—" for f in result.floors)
        sharp_txt = " / ".join(f"{f.sharpness:.0f}" for f in result.floors)

        items = (
            _item("จุดในบัฟเฟอร์", f"{len(df)}")
            + _item("สถานะข้อมูล",
                    "ขยับปกติ" if stuck == 0 else f"นิ่งมา {stuck} รอบ",
                    "ok" if stuck == 0 else "bad")
            + _item("อัตราสุ่มจริง (fs)", f"{result.fs:.2f} Hz")
            + _item("NYQUIST", f"{result.fs / 2:.1f} Hz")
            + _item("คาบเฉลี่ย (dt median)", f"{dt_med:.1f} ms")
            + _item("โหมดที่ใช้",
                    "ไซน์คงที่" if result.active_mode == "sine" else "ติดตาม fn")
            + _item("ตรวจพบสัญญาณไซน์", "ใช่" if result.sine_detected else "ไม่")
            + _item("ความคมของพีค", sharp_txt)
            + _item("fn ชั้น 1/2/3 (Hz)", fn_txt)
            + _item("แอมพลิจูด 1/2/3", amp_txt)
            + _item("T21 · coherence",
                    f"{result.T21:.3f} · {result.coh21:.2f}" if result.T21 else "—")
            + _item("T32 · coherence",
                    f"{result.T32:.3f} · {result.coh32:.2f}" if result.T32 else "—")
            + _item("เวลาประมวลผล", f"{elapsed:.0f} ms",
                    "ok" if elapsed < C.REFRESH_MS else "bad")
            + _item("คีย์ล่าสุดที่ดึงได้", f"{client.last_key or '—'}")
        )
        st.markdown(f'<div class="sv-dbg">{items}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="sv-dbg-url">แหล่งข้อมูล: '
            f'{C.FIREBASE_DOMAIN or "—ยังไม่ตั้งค่า—"}/{C.DB_PATH}.json</div>',
            unsafe_allow_html=True)
