"""services/telegram.py — แจ้งเตือนผ่าน Telegram Bot

⚠️ ปัญหาที่ต้องแก้: dashboard auto-refresh ทุก 1.5 วินาที = 2,400 รอบ/ชม.
   ถ้าไม่กัน จะยิงข้อความซ้ำจนโดน Telegram แบนใน 2 นาที

ป้องกัน 3 ชั้น:
  1. edge-triggered  — ยิงเฉพาะตอน "สถานะเปลี่ยน" ไม่ใช่ตอน "สถานะเป็น"
  2. cooldown        — ห้ามยิง event เดิมซ้ำภายใน COOLDOWN_SEC
  3. cache_resource  — เก็บ state ระดับ process ไม่ใช่ session
                       (ถ้าใช้ session_state เปิด 3 แท็บจะยิง 3 ครั้ง)

ตั้งค่า: BotFather → /newbot เอา token
        @userinfobot → เอา chat_id
        ใส่ใน .streamlit/secrets.toml
"""
import time
import requests
import streamlit as st

from config import FLOOR_NAMES, _secret

COOLDOWN_SEC    = 300     # ห้ามส่ง event เดิมซ้ำใน 5 นาที
HEALTH_DROP_PCT = 15.0    # Health ตกเกินกี่ %
HEALTH_WINDOW_S = 600.0   # ...ภายในกี่วินาที


def _cfg(key: str) -> str:
    """ใช้ตัวอ่านเดียวกับ config.py — รองรับทั้ง st.secrets / ไฟล์ / env var"""
    return _secret(key, "")


@st.cache_resource
def _state():
    """state ร่วมระดับ process — ทุก session/แท็บใช้ก้อนเดียวกัน"""
    return {"last_sent": {}, "prev_status": {}, "health_log": {}, "prev_stuck": False}


def enabled() -> bool:
    return bool(_cfg("TELEGRAM_TOKEN") and _cfg("TELEGRAM_CHAT_ID"))


def _send(text: str) -> bool:
    token, chat = _cfg("TELEGRAM_TOKEN"), _cfg("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "parse_mode": "HTML"},
            timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False


def _fire(event_key: str, text: str, cooldown: float = COOLDOWN_SEC) -> bool:
    """ชั้นที่ 2: ส่งเฉพาะเมื่อพ้น cooldown ของ event นั้นแล้ว"""
    st_ = _state()
    now = time.time()
    if now - st_["last_sent"].get(event_key, 0.0) < cooldown:
        return False
    if _send(text):
        st_["last_sent"][event_key] = now
        return True
    return False


# ------------------------------------------------------------
def on_status_change(floor_idx: int, status: str, pct):
    """ชั้นที่ 1: ยิงเฉพาะตอนสถานะเปลี่ยนจริง"""
    st_ = _state()
    prev = st_["prev_status"].get(floor_idx)
    st_["prev_status"][floor_idx] = status
    if prev is None or prev == status:
        return

    name = FLOOR_NAMES[floor_idx]
    p = f"{pct:.1f}%" if pct is not None else "—"

    if status == "red":
        _fire(f"red_{floor_idx}",
              f"🔴 <b>เตือนภัย: {name}</b>\n"
              f"สถานะ {prev} → <b>อันตราย</b>\n"
              f"Health เทียบ baseline: <b>{p}</b>\n"
              f"⚠️ ควรหยุดการทดลองและตรวจจุดยึดของชั้นนี้")
    elif status == "yellow" and prev == "green":
        _fire(f"yellow_{floor_idx}",
              f"🟡 <b>เฝ้าระวัง: {name}</b>\nHealth ลดเหลือ <b>{p}</b>")
    elif status == "green" and prev != "green":
        _fire(f"recover_{floor_idx}",
              f"🟢 <b>กลับสู่ปกติ: {name}</b>\nHealth ฟื้นเป็น <b>{p}</b>")


def on_stuck(stuck_counter: int, threshold: int = 4):
    st_ = _state()
    is_stuck = stuck_counter >= threshold
    was = st_["prev_stuck"]
    st_["prev_stuck"] = is_stuck

    if is_stuck and not was:
        _fire("stuck",
              "🚨 <b>ข้อมูลหยุดนิ่ง</b>\nตรวจสอบตามลำดับ:\n"
              "1. heartbeat/server_ts ใน Firebase ขยับไหม\n"
              "2. WiFi ของ ESP32\n"
              "3. โควตา bandwidth ของ Firebase")
    elif was and not is_stuck:
        _fire("stuck_ok", "✅ <b>ข้อมูลกลับมาแล้ว</b>")


def on_health_sample(floor_idx: int, pct):
    """ชั้นที่ 3: Health ตกเกิน HEALTH_DROP_PCT ภายใน HEALTH_WINDOW_S"""
    if pct is None:
        return
    st_ = _state()
    now = time.time()
    log = st_["health_log"].setdefault(floor_idx, [])
    log.append((now, float(pct)))
    st_["health_log"][floor_idx] = [x for x in log if now - x[0] <= HEALTH_WINDOW_S]
    log = st_["health_log"][floor_idx]
    if len(log) < 5:
        return
    oldest = log[0][1]
    drop = oldest - pct
    if drop >= HEALTH_DROP_PCT:
        _fire(f"drop_{floor_idx}",
              f"📉 <b>Health ร่วงเร็ว: {FLOOR_NAMES[floor_idx]}</b>\n"
              f"{oldest:.1f}% → {pct:.1f}% "
              f"(ลด {drop:.1f}% ใน {HEALTH_WINDOW_S/60:.0f} นาที)")


def test() -> bool:
    return _send("✅ SmartVibe เชื่อมต่อ Telegram สำเร็จ")
