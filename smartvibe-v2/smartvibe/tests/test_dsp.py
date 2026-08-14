"""ทดสอบ core/dsp.py — รันด้วย: pytest tests/ -v"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

import numpy as np
import pytest
from core import dsp


FS = 50.0


def make_sine(f, seconds=12.0, amp=1.0, noise=0.02, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(0, seconds, 1 / FS)
    return amp * np.sin(2 * np.pi * f * t) + noise * rng.standard_normal(len(t))


def test_peak_frequency_accurate():
    """หาความถี่พีคได้แม่นภายใน 0.1 Hz"""
    fw, psd = dsp.compute_psd(make_sine(8.0), FS)
    f, sharp = dsp.peak_frequency(fw, psd, fs=FS)
    assert abs(f - 8.0) < 0.1
    assert sharp > 40          # sine บริสุทธิ์ต้องคมมาก


def test_search_hi_clamped_to_nyquist():
    """SEARCH_HI ต้องไม่เกิน Nyquist — บั๊กเดิมค้นถึง 15 Hz ทั้งที่ Nyquist = 10"""
    fw, psd = dsp.compute_psd(make_sine(8.0), 20.0)
    f, _ = dsp.peak_frequency(fw, psd, fs=20.0)
    assert f is not None and f <= 20.0 * 0.45


def test_band_rms_scale_invariant_to_nperseg():
    """แก้บั๊กหลัก: ค่าต้องไม่เปลี่ยนตามความยาวข้อมูล"""
    long_sig = make_sine(8.0, seconds=20.0)
    short_sig = long_sig[:600]
    fw1, p1 = dsp.compute_psd(long_sig, FS)
    fw2, p2 = dsp.compute_psd(short_sig, FS)
    a1 = dsp.band_rms(fw1, p1, 7.5, 8.5)
    a2 = dsp.band_rms(fw2, p2, 7.5, 8.5)
    assert abs(a1 - a2) / a1 < 0.15, f"ค่าต่างกัน {abs(a1-a2)/a1:.1%} มากเกินไป"


def test_band_rms_matches_time_domain():
    """sqrt(∫PSD df) ต้องเท่ากับ RMS ในโดเมนเวลา (ทฤษฎีบทพาร์เซอวาล)"""
    sig = make_sine(8.0, amp=2.0, noise=0.0)
    fw, psd = dsp.compute_psd(sig, FS)
    spectral = dsp.band_rms(fw, psd, 0, FS / 2)
    temporal = np.sqrt(np.mean((sig - sig.mean()) ** 2))
    assert abs(spectral - temporal) / temporal < 0.05


def test_estimate_fs():
    t = np.arange(0, 1000, 20.0)
    assert abs(dsp.estimate_fs(t) - 50.0) < 0.1


def test_transmissibility_gain():
    """สัญญาณออกแรงกว่าเข้า 2.5 เท่า → T ควรได้ ~2.5"""
    rng = np.random.default_rng(1)
    x = rng.standard_normal(1200)
    y = 2.5 * x
    T, coh = dsp.transmissibility_h1(x, y, FS, 8.0, half=2.0)
    assert coh > 0.95
    assert abs(T - 2.5) < 0.1


def test_transmissibility_rejects_low_coherence():
    """สัญญาณไม่เกี่ยวกันเลย → ต้องคืน None (ไม่ให้ตัดสิน)"""
    rng = np.random.default_rng(2)
    T, coh = dsp.transmissibility_h1(rng.standard_normal(1200),
                                     rng.standard_normal(1200), FS, 8.0)
    assert T is None
    assert coh < 0.75


def test_tracked_peak_finds_shifted_peak():
    """broadband: พีคเลื่อนจาก 8 → 7 Hz ต้องตามเจอ"""
    fw, psd = dsp.compute_psd(make_sine(7.0, noise=0.3), FS)
    f_pk, amp, shift = dsp.tracked_peak(fw, psd, center=8.0, half=2.0)
    assert abs(f_pk - 7.0) < 0.3
    assert shift < -0.5        # เลื่อนลง
    assert amp > 0
