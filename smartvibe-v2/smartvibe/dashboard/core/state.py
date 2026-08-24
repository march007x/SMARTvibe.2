"""core/state.py — จัดการ st.session_state ที่เดียว

รวมไว้ที่นี่เพื่อไม่ให้ setdefault กระจายเต็มโค้ด
"""
import time

import config as C


def init(ss):
    ss.setdefault("last_uptime", 0)
    ss.setdefault("stuck_counter", 0)
    ss.setdefault("log_t0", time.time())
    ss.setdefault("last_log_time", 0.0)
    ss.setdefault("base_T21", None)
    ss.setdefault("base_T32", None)
    ss.setdefault("T_hist21", [])
    ss.setdefault("T_hist32", [])
    ss.setdefault("health_log", [])
    for i in range(C.N_FLOORS):
        ss.setdefault(f"base_fn{i}", None)
        ss.setdefault(f"fn_hist{i}", [])
        ss.setdefault(f"amp_hist{i}", [])
        ss.setdefault(f"status{i}", "green")
        ss.setdefault(f"consec{i}", 0)
        ss.setdefault(f"consec_dir{i}", None)


def lock_baseline(ss, result) -> bool:
    """ล็อกค่าอ้างอิงตอนโครงสร้างสมบูรณ์ คืน False ถ้าเงื่อนไขไม่พร้อม"""
    if not result.excitation_ok:
        return False
    if any(f.fn is None for f in result.floors):
        return False
    if result.active_mode == "sine" and result.T21 is None:
        return False

    for i, fr in enumerate(result.floors):
        ss[f"base_fn{i}"] = fr.fn
        ss[f"status{i}"] = "green"
        ss[f"consec{i}"] = 0
        ss[f"consec_dir{i}"] = None
    ss["base_T21"], ss["base_T32"] = result.T21, result.T32
    return True


def reset_all(ss):
    for i in range(C.N_FLOORS):
        ss[f"base_fn{i}"] = None
        ss[f"fn_hist{i}"] = []
        ss[f"amp_hist{i}"] = []
        ss[f"status{i}"] = "green"
        ss[f"consec{i}"] = 0
        ss[f"consec_dir{i}"] = None
    ss["base_T21"] = ss["base_T32"] = None
    ss["T_hist21"], ss["T_hist32"] = [], []
    ss["health_log"] = []
    ss["log_t0"] = time.time()
    ss["last_log_time"] = 0.0
    ss.pop("ai_result", None)
    ss.pop("ai_trend", None)
    ss.pop("ai_job", None)


def log_health(ss, result) -> bool:
    """เก็บ Health ลง health_log ทุก ๆ TREND_SAMPLE_SEC วินาที

    🐛 บั๊กเดิม: ss["health_log"] ถูกสร้างไว้แต่ไม่มีใครเขียนลงไปเลย
       ทำให้ ai_assistant.analyze_trend() ไม่มีข้อมูลป้อน ใช้งานไม่ได้จริง

    ⚠️ ห้ามเก็บทุกรอบ refresh (1.5 วิ) ไม่งั้น 1 ชั่วโมงได้ 2,400 จุด
       กิน RAM และทำให้ prompt ที่ส่งให้ AI ยาวเกินจำเป็น

    คืน True ถ้ารอบนี้บันทึกจริง
    """
    if not result.excitation_ok:
        return False                      # แรงกระตุ้นต่ำ ค่าไม่น่าเชื่อ ไม่ต้องบันทึก
    healths = [f.health for f in result.floors]
    if all(h is None for h in healths):
        return False                      # ยังไม่ได้ล็อก baseline

    now = time.time()
    if now - ss["last_log_time"] < C.TREND_SAMPLE_SEC:
        return False
    ss["last_log_time"] = now

    ss["health_log"].append({
        "t": round(now - ss["log_t0"], 1),
        "h": [round(h, 1) if h is not None else None for h in healths],
        "fn": [round(f.fn, 3) if f.fn else None for f in result.floors],
        "mode": result.active_mode,
    })
    if len(ss["health_log"]) > C.TREND_MAX_POINTS:
        del ss["health_log"][:-C.TREND_MAX_POINTS]
    return True


def update_stuck(ss, df) -> int:
    """นับว่าข้อมูลไม่ขยับมากี่รอบแล้ว"""
    cur = df["uptime_ms"].iloc[-1]
    if cur == ss.last_uptime:
        ss.stuck_counter += 1
    else:
        ss.stuck_counter, ss.last_uptime = 0, cur
    return ss.stuck_counter
