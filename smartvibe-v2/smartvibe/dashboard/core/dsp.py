"""core/dsp.py — ประมวลผลสัญญาณล้วน ๆ

โมดูลนี้ไม่ import streamlit เลย → เขียน unit test ได้โดยตรง
รันเทสต์: pytest tests/test_dsp.py
"""
import numpy as np
from scipy.signal import welch, csd, coherence

import config as C

# numpy 2.x เอา np.trapz ออกแล้ว เหลือ np.trapezoid
try:
    _integrate = np.trapezoid
except AttributeError:          # numpy 1.x
    _integrate = np.trapz


def estimate_fs(t_ms: np.ndarray, nominal: float = C.NOMINAL_FS) -> float:
    """ประมาณอัตราสุ่มตัวอย่างจริงจาก median ของ dt"""
    dt = np.diff(np.asarray(t_ms, dtype=float))
    dt = dt[(dt >= 5) & (dt <= 150)]
    return float(1000.0 / np.median(dt)) if len(dt) >= 10 else nominal


def resample_uniform(t_ms: np.ndarray, sig: np.ndarray, fs: float) -> np.ndarray:
    """แปลงสัญญาณที่ timestamp ไม่สม่ำเสมอให้เป็นระยะเท่ากัน"""
    t = (np.asarray(t_ms, float) - t_ms[0]) / 1000.0
    if t[-1] <= 0:
        return np.asarray(sig, float)
    return np.interp(np.arange(0.0, t[-1], 1.0 / fs), t, np.asarray(sig, float))


def compute_psd(sig: np.ndarray, fs: float):
    """Welch PSD ด้วย nperseg คงที่

    🐛 บั๊กเดิม: nperseg = min(256, max(64, len(sig)//2)) เปลี่ยนตาม
    จำนวนจุดที่ fetch ได้ → df = fs/nperseg แกว่ง → ค่าแอมพลิจูด
    กระโดดเองโดยโครงสร้างไม่ได้เปลี่ยนอะไรเลย
    """
    sig = np.asarray(sig, float)
    n = min(C.NPERSEG, len(sig))
    if n < 64:
        return None, None
    return welch(sig, fs=fs, nperseg=n, noverlap=n // 2,
                 window="hann", detrend="linear", scaling="density")


def band_rms(fw, psd, lo: float, hi: float) -> float:
    """RMS ในย่านความถี่ = sqrt(∫ PSD df)

    🐛 บั๊กเดิม: sqrt(np.sum(psd[m])) ลืมคูณ df
    PSD มีหน่วย g²/Hz การ sum เฉย ๆ ไม่ใช่พลังงาน และค่าจะ scale
    ตาม resolution ของสเปกตรัม
    """
    m = (fw >= lo) & (fw <= hi)
    if not m.any():
        return 0.0
    return float(np.sqrt(max(_integrate(psd[m], fw[m]), 0.0)))


def _parabolic(fw, psd, idx: int) -> float:
    """interpolate ยอดพีคแบบ log-parabolic ให้ละเอียดกว่าความกว้าง bin"""
    if idx <= 0 or idx >= len(psd) - 1:
        return float(fw[idx])
    y0, y1, y2 = (np.log(psd[j] + 1e-20) for j in (idx - 1, idx, idx + 1))
    den = y0 - 2 * y1 + y2
    d = float(np.clip(0.5 * (y0 - y2) / den, -0.5, 0.5)) if abs(den) > 1e-12 else 0.0
    return float(fw[idx] + d * (fw[1] - fw[0]))


def peak_frequency(fw, psd, fs=None, lo=C.SEARCH_LO, hi=C.SEARCH_HI):
    """หาพีคเด่นที่สุดในย่านค้นหา คืน (ความถี่, ความคม)

    🐛 บั๊กเดิม: SEARCH_HI = 15 Hz แต่ NOMINAL_FS = 20 → Nyquist = 10 Hz
    ค้นเหนือ 10 Hz ไม่มีทางเจอ และถ้า fn จริงอยู่เหนือ Nyquist
    สัญญาณจะ alias พับลงมาเป็นพีคปลอม
    """
    if fs is not None:
        hi = min(hi, fs * 0.45)
    m = (fw >= lo) & (fw <= hi)
    if not m.any():
        return None, 0.0
    band = psd[m]
    idx = np.where(m)[0][int(np.argmax(band))]
    sharp = float(psd[idx] / (np.median(band) + 1e-20))
    return _parabolic(fw, psd, idx), sharp


def tracked_peak(fw, psd, center, half=C.TRACK_HALF):
    """ตามล่าพีคใหม่ในหน้าต่าง ±half รอบ center

    คืน (ความถี่พีค, RMS ที่พีค, Δf เทียบ center)

    ⚠️⚠️ ข้อจำกัดเชิงฟิสิกส์ที่ต้องเข้าใจก่อนใช้:
    ภายใต้การกระตุ้นด้วย sine ความถี่เดียวใน steady state การตอบสนอง
    ของโครงสร้างจะมีพลังงานอยู่ที่ f_drive เท่านั้น — fn ของตึกไม่
    ปรากฏในสเปกตรัมเลย (โผล่แค่ช่วง transient สั้น ๆ ตอนเปิด/ปิดลำโพง)
    ฟังก์ชันนี้จึงจะคืนค่า f_drive เหมือนเดิมทุกครั้ง ตามล่า fn ไม่ได้

    ใช้ได้ก็ต่อเมื่อสัญญาณกระตุ้นมีองค์ประกอบ broadband:
    white noise / chirp sweep / การเคาะกระแทก / เสียงรบกวนรอบข้าง
    ถ้ายังใช้ sine บริสุทธิ์ ต้องเปลี่ยนวิธีทดลอง ไม่ใช่เปลี่ยนโค้ด
    """
    if center is None:
        return None, 0.0, 0.0
    m = (fw >= center - half) & (fw <= center + half)
    if not m.any():
        return None, 0.0, 0.0
    idx = np.where(m)[0][int(np.argmax(psd[m]))]
    f_pk = _parabolic(fw, psd, idx)
    df = fw[1] - fw[0]
    amp = band_rms(fw, psd, f_pk - 3 * df, f_pk + 3 * df)
    return f_pk, amp, float(f_pk - center)


def wideband_energy(fw, psd, fs=None, lo=C.SEARCH_LO, hi=C.SEARCH_HI) -> float:
    """พลังงานรวมในย่านกว้าง — ตัวชี้วัดสำรองที่ไม่ขึ้นกับตำแหน่งพีค"""
    if fs is not None:
        hi = min(hi, fs * 0.45)
    return band_rms(fw, psd, lo, hi)


def transmissibility_h1(sig_in, sig_out, fs, f_center, half=0.5):
    """T = |Sxy/Sxx| (H1 estimator) พร้อม coherence gate

    ดีกว่า amp_out/amp_in แบบเดิมเพราะ:
    - ใช้ข้อมูล cross-spectrum ทนต่อ noise ที่เอาต์พุตได้ดีกว่า
    - coherence บอกตรง ๆ ว่าข้อมูลรอบนี้เชื่อได้ไหม

    คืน (T, coherence) — T เป็น None ถ้า coherence ต่ำกว่าเกณฑ์
    """
    n = min(C.NPERSEG, len(sig_in), len(sig_out))
    if n < 64:
        return None, 0.0
    kw = dict(fs=fs, nperseg=n, noverlap=n // 2, window="hann", detrend="linear")
    f, Pxx = welch(sig_in, **kw)
    _, Pxy = csd(sig_in, sig_out, **kw)
    _, Cxy = coherence(sig_in, sig_out, **kw)

    m = (f >= f_center - half) & (f <= f_center + half)
    if not m.any():
        return None, 0.0
    T = float(np.abs(np.sum(Pxy[m]) / (np.sum(Pxx[m]) + 1e-20)))
    coh = float(np.mean(Cxy[m]))
    return (T if coh >= C.COH_MIN else None), coh
