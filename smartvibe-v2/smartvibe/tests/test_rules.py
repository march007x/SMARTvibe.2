"""ทดสอบ core/rules.py — ตัวสรุปผลจากกฎวิศวกรรม

จุดสำคัญ: rules.py ไม่ import streamlit จึงป้อน object ปลอมเข้าไปทดสอบได้ตรง ๆ
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

import config as C                                   # noqa: E402
from config import Thresholds                        # noqa: E402
from core import rules                               # noqa: E402
from core.analysis import AnalysisResult, FloorResult  # noqa: E402

TH = Thresholds()


def make_result(mode="sine", T21=1.70, T32=1.38, coh=0.98,
                fns=(11.0, 11.0, 11.0), amps=(0.09, 0.15, 0.22),
                rms=0.05, healths=(None, None, None), n=900):
    r = AnalysisResult(fs=50.0, active_mode=mode, n_points=n,
                       f_drive=11.0, excitation_ok=rms >= TH.rms_min,
                       T21=T21, T32=T32, coh21=coh, coh32=coh)
    for i in range(3):
        fr = FloorResult(index=i, fn=fns[i], amp=amps[i], rms=rms,
                         sharpness=60.0, health=healths[i])
        r.floors.append(fr)
    return r


def base_ss(**kw):
    ss = {"base_T21": 1.70, "base_T32": 1.38,
          "base_fn0": 11.0, "base_fn1": 11.0, "base_fn2": 11.0}
    ss.update(kw)
    return ss


# ------------------------------------------------------------------
#  ยังไม่ล็อก baseline
# ------------------------------------------------------------------
def test_no_baseline_asks_to_lock():
    ss = {"base_T21": None, "base_T32": None,
          "base_fn0": None, "base_fn1": None, "base_fn2": None}
    v = rules.evaluate(make_result(), ss, TH)
    assert v.level == "info"
    assert "ค่าอ้างอิง" in v.headline
    assert any("ล็อก" in a for a in v.actions)


# ------------------------------------------------------------------
#  โหมดไซน์ — ระบุตำแหน่งจาก Transmissibility
# ------------------------------------------------------------------
def test_healthy_reports_ok():
    v = rules.evaluate(make_result(), base_ss(), TH)
    assert v.level == "ok"
    assert "ไม่พบ" in v.headline


def test_span2_damage_is_localised():
    # T21 เปลี่ยน 25% ส่วน T32 นิ่ง → ต้องชี้ช่วงชั้น 2
    v = rules.evaluate(make_result(T21=1.70 * 1.25), base_ss(), TH)
    assert v.level == "danger"
    assert "ช่วงชั้น 2" in v.headline
    assert "ช่วงชั้น 3" not in v.headline


def test_span3_damage_is_localised():
    v = rules.evaluate(make_result(T32=1.38 * 1.25), base_ss(), TH)
    assert v.level == "danger"
    assert "ช่วงชั้น 3" in v.headline


def test_small_change_stays_ok():
    # เปลี่ยนแค่ 5% ยังไม่ถึงเกณฑ์ 10% → ต้องไม่ตื่นตูม
    v = rules.evaluate(make_result(T21=1.70 * 1.05), base_ss(), TH)
    assert v.level == "ok"


def test_both_spans_same_direction_is_global():
    v = rules.evaluate(make_result(T21=1.70 * 1.25, T32=1.38 * 1.25),
                       base_ss(), TH)
    assert "ทั้งโครงสร้าง" in v.headline


# ------------------------------------------------------------------
#  โหมดติดตาม fn — ประเมินความรุนแรง
# ------------------------------------------------------------------
def test_fn_mode_detects_stiffness_loss():
    # fn ลด 10% → Health = 0.9² = 81% → ต่ำกว่า g2y(90) แต่ยังไม่ต่ำกว่า y2r(70)
    v = rules.evaluate(
        make_result(mode="fn", fns=(9.9, 9.9, 9.9), healths=(81.0, 81.0, 81.0)),
        base_ss(), TH)
    assert v.level == "warn"
    assert "แข็งเกร็ง" in v.headline


def test_fn_mode_uniform_drop_says_cannot_localise():
    v = rules.evaluate(
        make_result(mode="fn", fns=(9.9, 9.9, 9.9), healths=(81.0, 81.0, 81.0)),
        base_ss(), TH)
    assert "ระบุตำแหน่งไม่ได้" in v.summary


# ------------------------------------------------------------------
#  ประตูคุณภาพข้อมูล
# ------------------------------------------------------------------
def test_weak_excitation_lowers_confidence_and_warns():
    v = rules.evaluate(make_result(rms=0.001), base_ss(), TH)
    assert v.confidence < 60
    assert any("แรงสั่น" in f.title for f in v.findings)


def test_low_coherence_is_flagged():
    v = rules.evaluate(make_result(coh=0.40), base_ss(), TH)
    assert any("เชื่อถือไม่ได้" in f.title for f in v.findings)
    assert v.level != "ok"          # ห้ามสรุปว่าปกติเมื่อข้อมูลเชื่อไม่ได้


def test_clean_data_gives_high_confidence():
    v = rules.evaluate(make_result(), base_ss(), TH)
    assert v.confidence >= 80


def test_confidence_is_bounded():
    for r in (make_result(rms=0.0001, coh=0.1, n=50), make_result()):
        v = rules.evaluate(r, base_ss(), TH)
        assert 5 <= v.confidence <= 99


# ------------------------------------------------------------------
#  ผลลัพธ์ต้องคงที่ (deterministic) — จุดขายหลักเทียบกับ LLM
# ------------------------------------------------------------------
def test_same_input_gives_identical_output():
    a = rules.evaluate(make_result(T21=1.70 * 1.25), base_ss(), TH)
    b = rules.evaluate(make_result(T21=1.70 * 1.25), base_ss(), TH)
    assert (a.level, a.headline, a.summary, a.confidence) == \
           (b.level, b.headline, b.summary, b.confidence)


def test_ok_headline_never_contradicts_warn_badge():
    """ป้ายบอก 'เฝ้าระวัง' แต่พาดหัวบอก 'ไม่พบความผิดปกติ' = ขัดกันเอง ห้ามเกิด"""
    v = rules.evaluate(make_result(coh=0.40), base_ss(), TH)
    assert v.level == "warn"
    assert "ไม่พบ" not in v.headline


def test_no_transmissibility_does_not_claim_healthy():
    """coherence ต่ำจน dsp คืน T = None → ต้องบอกว่า 'อ่านไม่ได้' ไม่ใช่ 'ปกติ'"""
    v = rules.evaluate(make_result(T21=None, T32=None, coh=0.30), base_ss(), TH)
    assert "ปกติ" not in v.headline
    assert v.level != "ok"
