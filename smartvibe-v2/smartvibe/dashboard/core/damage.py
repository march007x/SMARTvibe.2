"""core/damage.py — ตรรกะประเมินความเสียหายและเครื่องสถานะ

ฟังก์ชันทั้งหมดเป็น pure function ไม่พึ่ง streamlit → เทสต์ได้
"""
import numpy as np

from config import Thresholds, MIN_CONSEC


def health_from_fn(fn_now, fn_base):
    """Health = (fn/fn₀)² x 100 = % ของ stiffness ที่เหลืออยู่

    มาจาก fn ∝ sqrt(k/m) ดังนั้น k/k₀ = (fn/fn₀)²

    ⚠️ ใช้ได้เมื่อกระตุ้นด้วย white noise / sweep / เคาะกระแทกเท่านั้น
    ถ้ากระตุ้นด้วย sine ความถี่เดียว fn ที่วัดได้คือความถี่ลำโพง
    ไม่ใช่ของตึก → ตัวเลขนี้จะไม่มีความหมาย
    """
    if not fn_now or not fn_base:
        return None
    return float(np.clip((fn_now / fn_base) ** 2 * 100.0, 0.0, 130.0))


def similarity_pct(now, base):
    """ความคล้ายของค่าสองค่า 0-100% (ใช้กับ Transmissibility)

    เป็นค่าสมมาตร: T เพิ่มหรือลดก็ทำให้ % ลดลงเหมือนกัน
    """
    if base is None or now is None or base <= 0 or now <= 0:
        return None
    return float(100.0 * min(now, base) / max(now, base))


def next_status(status: str, consec: int, direction, pct: float, th: Thresholds):
    """เครื่องสถานะ 🟢🟡🔴 แบบต้องเข้าเงื่อนไขติดกัน MIN_CONSEC รอบ

    ป้องกันการกระพริบจาก noise รอบเดียว
    คืน (สถานะใหม่, ตัวนับ, ทิศทางล่าสุด)
    """
    if status == "green":
        consec = consec + 1 if pct < th.g2y else 0
        if consec >= MIN_CONSEC:
            return "yellow", 0, None
        return "green", consec, direction

    if status == "yellow":
        cur = "up" if pct >= th.y2g else ("down" if pct < th.y2r else None)
        if cur != direction:
            consec = 0
        if cur is None:
            return "yellow", 0, None
        consec += 1
        if consec >= MIN_CONSEC:
            return ("green" if cur == "up" else "red"), 0, None
        return "yellow", consec, cur

    # red
    consec = consec + 1 if pct >= th.r2y else 0
    if consec >= MIN_CONSEC:
        return "yellow", 0, None
    return "red", consec, direction


def median_filter(history: list, value: float, size: int) -> float:
    """ต่อค่าใหม่เข้า history แล้วคืน median (แก้ history ในที่)"""
    history.append(value)
    while len(history) > size:
        history.pop(0)
    return float(np.median(history))
