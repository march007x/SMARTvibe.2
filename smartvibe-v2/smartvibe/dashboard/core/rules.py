"""core/rules.py — ตัวสรุปผลจากกฎวิศวกรรม (rule-based expert system)

ทำหน้าที่เดียวกับ "ผู้ช่วยวิเคราะห์" แต่**ไม่พึ่ง AI ภายนอกเลย**
ทุกข้อสรุปมาจากกฎที่เขียนไว้ตรง ๆ ในไฟล์นี้ อ่านแล้วชี้ได้ทันทีว่า
บรรทัดไหนทำให้ระบบสรุปแบบนั้น

ทำไมต้องมีทั้งที่มี AI แล้ว
------------------------------------------------------------------
1. ไม่ต้องใช้อินเทอร์เน็ต ไม่ต้องใช้ API key ไม่มีโควตา
   → วันนำเสนอ ถ้า wifi ล่มหรือโควตาหมด หน้าจอนี้ยังทำงานครบ 100%
2. ผลลัพธ์เหมือนเดิมทุกครั้งที่ข้อมูลเหมือนเดิม (deterministic)
   ต่างจาก LLM ที่ตอบไม่เหมือนเดิมเป๊ะ ๆ
3. ตรวจสอบย้อนกลับได้ — กรรมการถามว่า "ทำไมถึงสรุปแบบนี้"
   เปิดไฟล์นี้ชี้กฎให้ดูได้เลย

หลักการทางวิศวกรรมที่ใช้
------------------------------------------------------------------
  fn  (ความถี่ธรรมชาติ)  บอกว่า  "มีความเสียหายไหม และรุนแรงแค่ไหน"
                          เพราะ fn ∝ √(k/m) → k ลด ทำให้ fn ลด
                          แต่บอกตำแหน่งไม่ได้ เพราะ fn เป็นค่าของทั้งตึก

  T   (Transmissibility)  บอกว่า  "ความเสียหายอยู่ช่วงชั้นไหน"
                          T21 = การขยายการสั่นจากชั้น 1 ไปชั้น 2
                          ถ้าจุดต่อช่วงไหนนิ่มลง สัดส่วนการขยับของช่วงนั้นจะเปลี่ยน

  ใช้สองตัวนี้คู่กันจึงตอบได้ทั้ง "เท่าไร" และ "ตรงไหน"

ไฟล์นี้ไม่ import streamlit → เขียน unit test ได้ตรง ๆ
"""
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

import config as C

# ---------- ค่าคงที่ของกฎ ----------
T_NOTABLE = 10.0    # T เปลี่ยนเกิน % นี้ = เริ่มมีนัยสำคัญ
T_STRONG  = 20.0    # เปลี่ยนเกิน % นี้ = ชัดเจน
FN_NOTABLE = 1.5    # fn เปลี่ยนเกิน % นี้ = เริ่มมีนัยสำคัญ (≈ Health 3%)
MIN_POINTS_OK = 600  # จำนวนจุดที่ถือว่าข้อมูลเต็มบัฟเฟอร์พอ

SPAN_NAMES = {2: "ช่วงชั้น 2 (จุดต่อระหว่างชั้น 1 กับชั้น 2)",
              3: "ช่วงชั้น 3 (จุดต่อระหว่างชั้น 2 กับชั้น 3)"}


@dataclass
class Finding:
    """ข้อสังเกตหนึ่งข้อ"""
    level: str          # ok | info | warn | danger
    title: str
    detail: str = ""


@dataclass
class Verdict:
    """ผลสรุปทั้งหมดที่ส่งให้ UI ไปวาด"""
    level: str = "info"
    headline: str = "กำลังรวบรวมข้อมูล"
    summary: str = ""
    confidence: int = 0
    confidence_note: str = ""
    findings: List[Finding] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)


# ------------------------------------------------------------------
#  ตัวช่วย
# ------------------------------------------------------------------
def _pct_change(now: Optional[float], base: Optional[float]) -> Optional[float]:
    """เปลี่ยนไปกี่ % จากค่าอ้างอิง (บวก = เพิ่มขึ้น)"""
    if now is None or base in (None, 0):
        return None
    return (now / base - 1.0) * 100.0


def _worst(level_a: str, level_b: str) -> str:
    order = ["ok", "info", "warn", "danger"]
    return level_a if order.index(level_a) >= order.index(level_b) else level_b


# ------------------------------------------------------------------
#  1) ประเมินว่า "ข้อมูลรอบนี้เชื่อได้แค่ไหน"
# ------------------------------------------------------------------
def assess_confidence(result, th) -> tuple:
    """คืน (คะแนน 0-100, เหตุผลข้อที่หักคะแนนมากที่สุด)

    ไม่ได้เดา — หักคะแนนตามเงื่อนไขที่วัดได้จริงทีละข้อ
    """
    score = 100.0
    reasons = []

    if result.n_points < 300:
        score -= 35; reasons.append((35, "ข้อมูลในบัฟเฟอร์ยังน้อย"))
    elif result.n_points < MIN_POINTS_OK:
        score -= 12; reasons.append((12, "บัฟเฟอร์ยังไม่เต็ม"))

    if not result.excitation_ok:
        score -= 40; reasons.append((40, "แรงสั่นสะเทือนต่ำกว่าเกณฑ์"))

    # อัตราสุ่มหลุดจากที่ออกแบบไว้ → สเปกตรัมเพี้ยน
    if abs(result.fs - C.NOMINAL_FS) / C.NOMINAL_FS > 0.20:
        score -= 15; reasons.append((15, "อัตราสุ่มจริงหลุดจากค่าออกแบบเกิน 20%"))

    # ความถี่กระตุ้นเข้าใกล้ Nyquist → เสี่ยง aliasing
    if result.f_drive and result.f_drive > result.fs * 0.40:
        score -= 20; reasons.append((20, "ความถี่กระตุ้นเข้าใกล้ขีดจำกัด Nyquist"))

    if result.active_mode == "sine":
        cohs = [c for c in (result.coh21, result.coh32) if c]
        if cohs and min(cohs) < C.COH_MIN:
            score -= 30; reasons.append((30, "coherence ต่ำกว่าเกณฑ์"))
        elif cohs:
            score -= (1.0 - float(np.mean(cohs))) * 60
            reasons.append((int((1.0 - float(np.mean(cohs))) * 60), "coherence ไม่เต็ม"))

    sharps = [f.sharpness for f in result.floors if f.sharpness > 0]
    if sharps and float(np.median(sharps)) < 8:
        score -= 15; reasons.append((15, "พีคในสเปกตรัมไม่คม แยกจากสัญญาณรบกวนได้ยาก"))

    if result.amp_ratio_hint:
        score -= 20; reasons.append((20, "รูปทรงการแกว่งของตึกผิดจากโหมดที่ 1"))

    note = max(reasons)[1] if reasons else "ข้อมูลครบและสัญญาณสะอาด"
    return int(np.clip(score, 5, 99)), note


# ------------------------------------------------------------------
#  2) ตรวจคุณภาพการทดลอง (ก่อนจะสรุปเรื่องความเสียหาย)
# ------------------------------------------------------------------
def check_setup(result, th) -> List[Finding]:
    out = []

    if not result.excitation_ok:
        weak = [C.FLOOR_NAMES[i] for i, f in enumerate(result.floors)
                if f.rms < th.rms_min]
        out.append(Finding(
            "warn", "แรงสั่นสะเทือนยังน้อยเกินไป",
            f"{', '.join(weak)} วัดค่า RMS ได้ต่ำกว่าเกณฑ์ {th.rms_min:.3f} g "
            "ค่าที่อ่านได้ในสภาพนี้เป็นสัญญาณรบกวนมากกว่าการสั่นจริง"))

    if result.f_drive and result.f_drive > result.fs * 0.40:
        out.append(Finding(
            "warn", "ความถี่กระตุ้นสูงเกินกว่าที่ระบบวัดได้อย่างปลอดภัย",
            f"กำลังขับที่ {result.f_drive:.1f} Hz ขณะที่อัตราสุ่มอยู่ที่ "
            f"{result.fs:.1f} Hz (Nyquist = {result.fs/2:.1f} Hz) "
            "ความถี่ที่สูงกว่านี้จะพับกลับลงมาเป็นพีคปลอม"))

    if result.active_mode == "sine":
        for name, coh in (("ช่วงชั้น 2", result.coh21), ("ช่วงชั้น 3", result.coh32)):
            if coh and coh < C.COH_MIN:
                out.append(Finding(
                    "warn", f"สัญญาณของ{name}ยังเชื่อถือไม่ได้",
                    f"coherence = {coh:.2f} ต่ำกว่าเกณฑ์ {C.COH_MIN:.2f} "
                    "แปลว่าการสั่นของสองชั้นนี้ไม่ได้มาจากแหล่งเดียวกันล้วน ๆ "
                    "มักเกิดจากเซ็นเซอร์หลวมหรือมีแรงอื่นมารบกวน"))

    if result.amp_ratio_hint:
        out.append(Finding("warn", "รูปทรงการแกว่งผิดจากโหมดที่ 1",
                           result.amp_ratio_hint))

    # โหมด sine แต่ 3 ชั้นเห็นความถี่ไม่ตรงกัน = มีชั้นจับฮาร์มอนิกมา
    fns = [f.fn for f in result.floors if f.fn]
    if result.active_mode == "sine" and len(fns) == C.N_FLOORS:
        spread = max(fns) - min(fns)
        if spread > 0.3:
            out.append(Finding(
                "warn", "ทั้งสามชั้นจับความถี่ได้ไม่ตรงกัน",
                f"ต่างกันถึง {spread:.2f} Hz ({' / '.join(f'{f:.2f}' for f in fns)} Hz) "
                "ขณะที่ถูกขับด้วยความถี่เดียว มักแปลว่ามีชั้นที่ไปจับฮาร์มอนิก "
                "หรือสัญญาณของชั้นนั้นอ่อนจนพีคจริงจมอยู่ในสัญญาณรบกวน"))

    if result.n_points < MIN_POINTS_OK:
        out.append(Finding("info", "บัฟเฟอร์ยังไม่เต็ม",
                           f"มี {result.n_points} จุด จากเป้าหมาย {C.BUFFER_SIZE} จุด "
                           "รอสักครู่ให้ข้อมูลสะสมครบก่อนตัดสินใจ"))
    return out


# ------------------------------------------------------------------
#  3) ระบุตำแหน่งความเสียหายจาก Transmissibility (โหมดไซน์)
# ------------------------------------------------------------------
def locate_by_transmissibility(result, ss) -> tuple:
    """คืน (ระดับ, พาดหัว, สรุป, รายการข้อสังเกต)

    กฎ: T ของ "ช่วงชั้น" ไหนเปลี่ยนจาก baseline มากที่สุด
        ความเสียหายอยู่ที่จุดต่อของช่วงชั้นนั้น
    """
    d21 = _pct_change(result.T21, ss.get("base_T21"))
    d32 = _pct_change(result.T32, ss.get("base_T32"))

    if d21 is None and d32 is None:
        # เกิดขึ้นจริงเมื่อ coherence ต่ำกว่าเกณฑ์ — dsp.transmissibility_h1()
        # จะคืน None แทนที่จะคืนตัวเลขที่เชื่อไม่ได้ ระบบจึงต้อง "ไม่สรุป"
        # ไม่ใช่สรุปว่าปกติ (การเงียบไม่เท่ากับผ่าน)
        return ("info", "รอบนี้ยังอ่านค่าไม่ได้",
                "สัญญาณของทั้งสองช่วงชั้นมี coherence ต่ำกว่าเกณฑ์ "
                f"{C.COH_MIN:.2f} ระบบจึงไม่นำมาคำนวณ เพื่อไม่ให้สรุปจากค่าที่เชื่อไม่ได้ "
                "— ยังไม่ได้แปลว่าโครงสร้างปกติหรือผิดปกติ", [])

    a21, a32 = abs(d21 or 0.0), abs(d32 or 0.0)
    found = []

    def _line(name, d, T, base):
        return Finding(
            "ok" if abs(d) < T_NOTABLE else ("danger" if abs(d) >= T_STRONG else "warn"),
            f"{name}: เปลี่ยนไป {d:+.1f}%",
            f"T ตอนนี้ {T:.3f} เทียบกับค่าอ้างอิง {base:.3f} — "
            + ("อยู่ในช่วงที่ถือว่าไม่เปลี่ยน" if abs(d) < T_NOTABLE else
               ("ชั้นบนขยับมากขึ้นเมื่อเทียบกับชั้นล่าง ซึ่งเป็นลักษณะของจุดต่อที่ "
                "นิ่มลง (k ลดลง)" if d > 0 else
                "ชั้นบนขยับน้อยลงเมื่อเทียบกับชั้นล่าง ซึ่งเกิดได้ทั้งจากจุดต่อที่ "
                "แข็งขึ้นและจากมวลที่เพิ่มขึ้น")))

    if d21 is not None:
        found.append(_line("ช่วงชั้น 2", d21, result.T21, ss["base_T21"]))
    if d32 is not None:
        found.append(_line("ช่วงชั้น 3", d32, result.T32, ss["base_T32"]))

    # --- ตัดสินตำแหน่ง ---
    if a21 < T_NOTABLE and a32 < T_NOTABLE:
        return ("ok", "ไม่พบความผิดปกติ",
                f"สัดส่วนการสั่นระหว่างชั้นยังเท่าเดิมทุกช่วง "
                f"(เปลี่ยนไม่เกิน {T_NOTABLE:.0f}%) โครงสร้างยังเหมือนตอนล็อกค่าอ้างอิง",
                found)

    if a21 >= T_NOTABLE and a32 < T_NOTABLE:
        lvl = "danger" if a21 >= T_STRONG else "warn"
        return (lvl, f"พบความผิดปกติที่ {SPAN_NAMES[2]}",
                f"เฉพาะช่วงชั้น 2 ที่สัดส่วนการสั่นเปลี่ยนไป {d21:+.1f}% "
                f"ส่วนช่วงชั้น 3 แทบไม่ขยับ ({d32:+.1f}%) "
                "รูปแบบนี้ชี้ไปที่จุดต่อระหว่างชั้น 1 กับชั้น 2 โดยตรง", found)

    if a32 >= T_NOTABLE and a21 < T_NOTABLE:
        lvl = "danger" if a32 >= T_STRONG else "warn"
        return (lvl, f"พบความผิดปกติที่ {SPAN_NAMES[3]}",
                f"เฉพาะช่วงชั้น 3 ที่สัดส่วนการสั่นเปลี่ยนไป {d32:+.1f}% "
                f"ส่วนช่วงชั้น 2 แทบไม่ขยับ ({d21:+.1f}%) "
                "รูปแบบนี้ชี้ไปที่จุดต่อระหว่างชั้น 2 กับชั้น 3 โดยตรง", found)

    # ทั้งสองช่วงเปลี่ยน
    lvl = "danger" if max(a21, a32) >= T_STRONG else "warn"
    if (d21 or 0) * (d32 or 0) > 0:
        return (lvl, "พบความผิดปกติแบบทั้งโครงสร้าง",
                f"ทั้งสองช่วงชั้นเปลี่ยนไปในทิศทางเดียวกัน "
                f"({d21:+.1f}% และ {d32:+.1f}%) ซึ่งมักไม่ได้เกิดจากจุดต่อจุดเดียว "
                "แต่เกิดจากฐานยึดหลวม มวลรวมเปลี่ยน หรือความถี่ที่ใช้กระตุ้น"
                "ไม่ตรงกับตอนล็อกค่าอ้างอิง — ตรวจสองอย่างหลังก่อนสรุปว่าเสียหาย", found)

    worst = 2 if a21 >= a32 else 3
    return (lvl, f"พบความผิดปกติที่ {SPAN_NAMES[worst]}",
            f"สองช่วงชั้นเปลี่ยนไปคนละทิศทาง ({d21:+.1f}% และ {d32:+.1f}%) "
            f"เป็นลักษณะของรูปทรงการแกว่งที่ถูกบิด ต้นตอมักอยู่ที่ช่วงที่เปลี่ยนมากกว่า "
            f"คือช่วงชั้น {worst}", found)


# ------------------------------------------------------------------
#  4) ประเมินความรุนแรงจาก fn (โหมดติดตามความถี่ธรรมชาติ)
# ------------------------------------------------------------------
def assess_by_fn(result, ss, th) -> tuple:
    rows, drops = [], []
    for i, fr in enumerate(result.floors):
        base = ss.get(f"base_fn{i}")
        d = _pct_change(fr.fn, base)
        if d is None:
            continue
        drops.append(d)
        h = fr.health
        lvl = "ok"
        if h is not None:
            lvl = "danger" if h < th.y2r else ("warn" if h < th.g2y else "ok")
        rows.append(Finding(
            lvl, f"{C.FLOOR_NAMES[i]}: fn {d:+.2f}%"
                 + (f" · Health {h:.1f}%" if h is not None else ""),
            f"ความถี่ {fr.fn:.2f} Hz เทียบค่าอ้างอิง {base:.2f} Hz — "
            + ("ยังอยู่ในช่วงปกติ" if abs(d) < FN_NOTABLE else
               ("ความถี่ลดลง แปลว่าความแข็งเกร็ง k ลดลงตาม fn ∝ √(k/m)"
                if d < 0 else
                "ความถี่เพิ่มขึ้น เกิดได้จากการขันจุดต่อแน่นขึ้นหรือมวลที่ลดลง"))))

    if not rows:
        return "info", "", "", []

    healths = [f.health for f in result.floors if f.health is not None]
    worst_h = min(healths) if healths else None
    mean_drop = float(np.mean(drops))
    spread = max(drops) - min(drops)

    if worst_h is None or worst_h >= th.g2y:
        return ("ok", "ไม่พบความผิดปกติ",
                f"ความถี่ธรรมชาติทุกชั้นยังใกล้ค่าอ้างอิง "
                f"(เปลี่ยนเฉลี่ย {mean_drop:+.2f}%) ความแข็งเกร็งของโครงสร้างยังครบ",
                rows)

    lvl = "danger" if worst_h < th.y2r else "warn"
    if spread < 1.0:
        summary = (f"ความถี่ลดลงพร้อมกันทั้งสามชั้นในอัตราใกล้เคียงกัน "
                   f"(เฉลี่ย {mean_drop:+.2f}%) เหลือความแข็งเกร็งต่ำสุด {worst_h:.1f}% "
                   "รูปแบบนี้เป็นความเสียหายระดับทั้งโครงสร้าง เช่น ฐานยึดหลวม "
                   "หรือมวลเพิ่ม — fn บอกได้ว่ามีปัญหาแต่ระบุตำแหน่งไม่ได้ "
                   "ต้องสลับไปโหมดไซน์เพื่ออ่านค่า Transmissibility จึงจะชี้ช่วงชั้นได้")
    else:
        i_worst = int(np.argmin([d if d is not None else 99 for d in drops]))
        summary = (f"ความถี่แต่ละชั้นลดไม่เท่ากัน (ต่างกัน {spread:.2f}%) "
                   f"โดย{C.FLOOR_NAMES[i_worst]}ลดมากที่สุด "
                   f"ความแข็งเกร็งต่ำสุดเหลือ {worst_h:.1f}%")
    return lvl, "พบความแข็งเกร็งลดลง", summary, rows


# ------------------------------------------------------------------
#  5) รวมทุกอย่างเป็นข้อสรุปเดียว
# ------------------------------------------------------------------
def evaluate(result, ss, th) -> Verdict:
    v = Verdict()
    v.confidence, v.confidence_note = assess_confidence(result, th)
    setup = check_setup(result, th)

    locked = (ss.get("base_T21") is not None if result.active_mode == "sine"
              else any(ss.get(f"base_fn{i}") is not None for i in range(C.N_FLOORS)))

    if not locked:
        v.level = "info"
        v.headline = "ยังไม่มีค่าอ้างอิงให้เปรียบเทียบ"
        v.summary = ("ระบบนี้ทำงานด้วยการเทียบสภาพปัจจุบันกับสภาพตอนโครงสร้างสมบูรณ์ "
                     "จึงต้องกดปุ่มล็อกค่าอ้างอิงขณะที่ตึกยังไม่มีความเสียหายก่อน "
                     "จากนั้นทุกค่าที่เห็นจะถูกวัดเทียบกับจุดนั้น")
        v.findings = setup
        v.actions = ["จัดตึกให้อยู่ในสภาพสมบูรณ์ ขันจุดต่อทุกจุดให้แน่น",
                     "เปิดแรงกระตุ้นให้นิ่งอย่างน้อย 20 วินาที",
                     "กดปุ่ม 🔒 ล็อก Baseline"]
        if not result.excitation_ok:
            v.actions.insert(0, "เพิ่มแรงสั่นก่อน — ตอนนี้ยังต่ำกว่าเกณฑ์จนล็อกไม่ได้")
        return v

    if result.active_mode == "sine":
        lvl, head, summ, rows = locate_by_transmissibility(result, ss)
    else:
        lvl, head, summ, rows = assess_by_fn(result, ss, th)

    v.level, v.headline, v.summary = lvl, head, summ
    v.findings = rows + setup

    # ---------- ประตูคุณภาพข้อมูล ----------
    # ถ้ารอบนี้ข้อมูลมีข้อสังเกต ห้ามประกาศว่า "ไม่พบความผิดปกติ"
    # เพราะการวัดที่ไม่น่าเชื่อถือทำให้ "มองไม่เห็น" ความเสียหายได้ด้วย
    # → เปลี่ยนพาดหัวให้ตรงกับป้ายสถานะ ไม่ให้ขัดกันเองบนหน้าจอ
    if any(f.level in ("warn", "danger") for f in setup) and v.level in ("ok", "warn"):
        if v.level == "ok":
            v.headline = "ยังยืนยันไม่ได้ในรอบนี้"
            v.summary = ("ค่าที่วัดได้ยังไม่ต่างจากค่าอ้างอิง แต่คุณภาพข้อมูลรอบนี้"
                         "มีข้อสังเกตตามรายการด้านล่าง การวัดที่ไม่นิ่งพออาจทำให้"
                         "มองไม่เห็นความเสียหายที่มีอยู่จริง จึงยังสรุปว่าปกติไม่ได้  —  "
                         + v.summary)
        else:
            v.summary += "  ⚠️ และรอบนี้คุณภาพข้อมูลยังมีข้อสังเกต ดูรายการด้านล่างก่อนสรุป"
        v.level = "warn"

    # ---------- สิ่งที่ควรทำต่อ ----------
    acts = []
    if not result.excitation_ok:
        acts.append("เพิ่มระดับแรงกระตุ้นให้ RMS ทุกชั้นเกิน "
                    f"{th.rms_min:.3f} g ก่อน ค่าปัจจุบันยังเชื่อไม่ได้")
    if result.active_mode == "sine" and min(result.coh21, result.coh32) < C.COH_MIN:
        acts.append("ตรวจว่าเซ็นเซอร์ทุกตัวยึดแน่นกับพื้นชั้น "
                    "และไม่มีสายไฟดึงรั้ง — coherence ต่ำมักมาจากตรงนี้")
    if result.amp_ratio_hint:
        acts.append("ปรับความถี่ลำโพงเข้าใกล้ความถี่ธรรมชาติของตึก "
                    "ให้แอมพลิจูดเรียงเพิ่มขึ้นตามความสูงเป็นขั้นบันได")
    if v.level == "ok":
        acts.append("สภาพปกติ เก็บข้อมูลต่อเนื่องไว้ดูแนวโน้ม")
    elif v.level in ("warn", "danger"):
        acts.append("ตรวจจุดต่อของช่วงชั้นที่ระบบชี้ ว่ามีน็อตหลวมหรือรอยแตกหรือไม่")
        acts.append("ทดลองซ้ำอีกรอบเพื่อยืนยันว่าค่าไม่ได้เปลี่ยนเพราะสัญญาณรบกวน")
    if result.active_mode == "fn":
        acts.append("ถ้าต้องการรู้ว่าเสียหายที่ช่วงชั้นไหน ให้เปิดแรงกระตุ้น"
                    "แบบไซน์ความถี่คงที่แล้วสลับเป็นโหมดไซน์")
    v.actions = acts[:4]
    return v
