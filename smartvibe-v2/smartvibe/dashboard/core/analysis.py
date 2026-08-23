"""core/analysis.py — ท่อประมวลผลหลัก: DataFrame ดิบ → ผลวิเคราะห์

รวมขั้นตอนทั้งหมดไว้ที่เดียว: resample → PSD → หาพีค → เลือกโหมด
→ คำนวณแอมพลิจูด/Transmissibility → คำนวณ Health

ไม่วาดอะไรทั้งสิ้น ส่วน UI อยู่ในโฟลเดอร์ ui/
"""
from dataclasses import dataclass, field
from typing import Optional, List

import numpy as np
import pandas as pd

import config as C
from core import dsp
from core.damage import health_from_fn, similarity_pct, median_filter


@dataclass
class FloorResult:
    index: int
    fn: Optional[float] = None          # ความถี่พีคที่กรอง median แล้ว
    sharpness: float = 0.0
    rms: float = 0.0
    amp: Optional[float] = None         # แอมพลิจูดที่ความถี่อ้างอิง
    wideband: float = 0.0               # พลังงานรวมย่านกว้าง (ตัวสำรอง)
    f_peak: Optional[float] = None      # พีคที่ตามล่าได้ (โหมด broadband)
    df_shift: float = 0.0               # Δf เทียบ baseline
    health: Optional[float] = None
    psd: Optional[np.ndarray] = None
    peaks: List[tuple] = field(default_factory=list)   # พีคเด่น 3 อันดับ (f, ความคม)


@dataclass
class AnalysisResult:
    fs: float = C.NOMINAL_FS
    freqs: Optional[np.ndarray] = None
    floors: List[FloorResult] = field(default_factory=list)
    active_mode: str = "fn"             # "fn" หรือ "sine"
    sine_detected: bool = False
    f_drive: Optional[float] = None
    excitation_ok: bool = False
    T21: Optional[float] = None
    T32: Optional[float] = None
    coh21: float = 0.0
    coh32: float = 0.0
    n_points: int = 0
    harmonic_floors: List[int] = field(default_factory=list)  # ชั้นที่จับฮาร์มอนิกมา
    amp_ratio_hint: str = ""            # คำเตือนเมื่อสัดส่วนแอมพลิจูดแบนผิดปกติ


def _detect_sine(fns, sharps, fn_hists) -> bool:
    """ตรวจว่ากำลังถูกกระตุ้นด้วย sine ความถี่เดียวหรือไม่

    เกณฑ์: พีคคมมาก หรือ (ทั้ง 3 ชั้นเห็นความถี่เดียวกัน และ ค่านิ่งผิดปกติ)
    """
    valid = [f for f in fns if f]
    very_sharp = float(np.median([s for s in sharps if s > 0] or [0])) > C.SINE_SHARP
    same_freq = len(valid) == C.N_FLOORS and (max(valid) - min(valid)) < 0.15
    cvs = [(np.std(h) / (np.mean(h) + 1e-12) * 100) if len(h) >= 3 else 99
           for h in fn_hists]
    frozen = all(c < 0.3 for c in cvs)
    return very_sharp or (same_freq and frozen)


def analyze(df: pd.DataFrame, ss, mode_choice: str, th) -> AnalysisResult:
    """ss = st.session_state (ใช้เก็บ history ของ median filter)"""
    res = AnalysisResult(n_points=len(df))
    t_ms = df["uptime_ms"].values.astype(float)
    res.fs = dsp.estimate_fs(t_ms)

    signals, spectra, fns, sharps = [], [], [], []

    # ---------- 1) แปลงสัญญาณ + สเปกตรัม ----------
    for i in range(C.N_FLOORS):
        col = f"AccX_CH{i}"
        fr = FloorResult(index=i)
        if col not in df.columns:
            signals.append(None); spectra.append(None)
            fns.append(None); sharps.append(0.0); res.floors.append(fr)
            continue

        sig = dsp.resample_uniform(t_ms, df[col].values.astype(float), res.fs)
        signals.append(sig)
        fr.rms = float(np.sqrt(np.mean((sig - np.mean(sig)) ** 2)))

        fw, psd = dsp.compute_psd(sig, res.fs)
        if fw is None:
            spectra.append(None); fns.append(None); sharps.append(0.0)
            res.floors.append(fr); continue

        spectra.append((fw, psd))
        if res.freqs is None:
            res.freqs = fw
        fr.psd = psd

        fn_raw, sh = dsp.peak_frequency(fw, psd, fs=res.fs)
        fr.sharpness = sh
        fr.fn = median_filter(ss[f"fn_hist{i}"], fn_raw, C.HISTORY_SIZE) if fn_raw else None
        fr.wideband = dsp.wideband_energy(fw, psd, fs=res.fs)
        fr.peaks = dsp.top_peaks(fw, psd, fs=res.fs)

        fns.append(fr.fn); sharps.append(sh)
        res.floors.append(fr)

    # ---------- 2) เลือกโหมดวิเคราะห์ ----------
    res.sine_detected = _detect_sine(fns, sharps, [ss[f"fn_hist{i}"] for i in range(C.N_FLOORS)])
    if mode_choice.startswith("อัตโนมัติ"):
        res.active_mode = "sine" if res.sine_detected else "fn"
    elif mode_choice.startswith("ติดตาม"):
        res.active_mode = "fn"
    else:
        res.active_mode = "sine"

    # เลือกความถี่อ้างอิงแบบพับฮาร์มอนิกกลับลงมาก่อน (ดู dsp.fundamental_of)
    res.f_drive, res.harmonic_floors = dsp.fundamental_of(fns)
    res.excitation_ok = all(f.rms >= th.rms_min for f in res.floors)

    # ---------- 3) แอมพลิจูด ----------
    for i, fr in enumerate(res.floors):
        if spectra[i] is None:
            continue
        fw, psd = spectra[i]

        if res.active_mode == "sine":
            # โหมด sine: อ่านที่ความถี่ลำโพง (ถูกต้องสำหรับ Transmissibility)
            center = res.f_drive
        else:
            # โหมด broadband: ตามล่าพีครอบ baseline ของชั้นนั้น
            center = ss.get(f"base_fn{i}") or fr.fn
            if center:
                f_pk, _, shift = dsp.tracked_peak(fw, psd, center)
                fr.f_peak, fr.df_shift = f_pk, shift

        if center:
            a_raw = dsp.band_rms(fw, psd, center - 0.5, center + 0.5)
            fr.amp = median_filter(ss[f"amp_hist{i}"], a_raw, C.HISTORY_SIZE)

    # ---------- 3.5) ตรวจว่าอาคาร "ขยายการสั่น" พอหรือไม่ ----------
    # ถ้าขับที่ความถี่ต่ำกว่าความถี่ธรรมชาติมาก ตึกจะขยับไปพร้อมกันแทบทั้งก้อน
    # อัตราส่วนแอมพลิจูดระหว่างชั้นจะแบนเกือบเท่ากับ 1 ทำให้แยกชั้นไม่ออก
    # และล็อก baseline ได้ค่าที่ไม่ไวต่อความเสียหาย
    amps = [f.amp for f in res.floors]
    if all(a for a in amps):
        top_ratio = amps[-1] / amps[0]
        if top_ratio < 1.25:
            res.amp_ratio_hint = (
                f"ชั้นบนสุดแกว่งแรงกว่าชั้นล่างเพียง {top_ratio:.2f} เท่า "
                "— ตึกยังแทบไม่ขยายการสั่น มักเกิดจากกระตุ้นที่ความถี่ห่างจาก "
                "ความถี่ธรรมชาติมาก ควรปรับความถี่เข้าใกล้เรโซแนนซ์ หรือเปลี่ยนเป็นการเคาะ")

    # ---------- 4) Transmissibility (H1 + coherence) ----------
    if res.active_mode == "sine" and res.f_drive and all(s is not None for s in signals):
        t21, res.coh21 = dsp.transmissibility_h1(signals[0], signals[1], res.fs, res.f_drive)
        t32, res.coh32 = dsp.transmissibility_h1(signals[1], signals[2], res.fs, res.f_drive)
        if t21:
            res.T21 = median_filter(ss["T_hist21"], t21, C.HISTORY_SIZE)
        if t32:
            res.T32 = median_filter(ss["T_hist32"], t32, C.HISTORY_SIZE)

    # ---------- 5) Health ----------
    if res.active_mode == "fn":
        for i, fr in enumerate(res.floors):
            fr.health = health_from_fn(fr.fn, ss.get(f"base_fn{i}"))
    else:
        res.floors[1].health = similarity_pct(res.T21, ss.get("base_T21"))
        res.floors[2].health = similarity_pct(res.T32, ss.get("base_T32"))

    return res
