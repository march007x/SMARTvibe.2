"""ทดสอบ core/damage.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

from config import Thresholds
from core.damage import health_from_fn, similarity_pct, next_status, median_filter

TH = Thresholds()


def test_health_formula():
    """k ลด 20% → fn ลด sqrt(0.8) → Health ควรได้ 80%"""
    assert abs(health_from_fn(10.0, 10.0) - 100.0) < 0.01
    assert abs(health_from_fn(10.0 * 0.8 ** 0.5, 10.0) - 80.0) < 0.01


def test_health_none_without_baseline():
    assert health_from_fn(8.0, None) is None


def test_similarity_symmetric():
    assert similarity_pct(2.0, 1.0) == similarity_pct(1.0, 2.0) == 50.0


def test_status_needs_consecutive_hits():
    """ต้องเข้าเงื่อนไขติดกัน 3 รอบถึงเปลี่ยนสถานะ — กันกระพริบจาก noise"""
    s, c, d = "green", 0, None
    for _ in range(2):
        s, c, d = next_status(s, c, d, 85.0, TH)
        assert s == "green"
    s, c, d = next_status(s, c, d, 85.0, TH)
    assert s == "yellow"


def test_status_single_dip_does_not_trigger():
    s, c, d = next_status("green", 0, None, 85.0, TH)   # ตก 1 รอบ
    s, c, d = next_status(s, c, d, 99.0, TH)            # กลับมาปกติ
    assert s == "green" and c == 0


def test_status_recovers_from_red():
    s, c, d = "red", 0, None
    for _ in range(3):
        s, c, d = next_status(s, c, d, 80.0, TH)
    assert s == "yellow"


def test_median_filter_rejects_spike():
    h = []
    for v in [8.0, 8.1, 7.9, 8.0, 99.0]:
        out = median_filter(h, v, 7)
    assert abs(out - 8.0) < 0.2      # spike ไม่มีผล
