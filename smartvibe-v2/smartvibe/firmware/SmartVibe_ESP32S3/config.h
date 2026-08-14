// ============================================================
//  config.h — ค่าคงที่ทั้งหมดของระบบ (ไม่มีความลับในไฟล์นี้)
//  แก้ค่าการทำงานทุกอย่างที่นี่ที่เดียว
// ============================================================
#pragma once

// ---------- Firebase ----------
// ⚠️ DB_PATH ต้องตรงกับ DB_PATH ใน dashboard/config.py เป๊ะ ๆ
#define DB_PATH    "/History3F"
#define META_PATH  "/History3F_meta"

// ---------- ขา I2C (ESP32-S3) ----------
#define I2C_SDA      8
#define I2C_SCL      9
#define TCA_ADDR     0x70
#define I2C_FREQ     400000

// ช่องของ TCA9548A ที่ต่อเซ็นเซอร์แต่ละชั้น
#define CH_FLOOR1    0
#define CH_FLOOR2    1
#define CH_FLOOR3    2
#define N_FLOORS     3

// ---------- อัตราการสุ่มตัวอย่าง ----------
#define SAMPLE_HZ    50
#define KEY_STEP_MS  (1000 / SAMPLE_HZ)   // 20 ms — ใช้เป็นระยะห่างของ key ด้วย

// ---------- การส่งข้อมูล ----------
#define BATCH_SIZE   25    // 25 samples = 500 ms ต่อการยิง 1 ครั้ง
#define QUEUE_DEPTH  8     // buffer 8 batch = 200 samples กันเน็ตหน่วง

// ส่งครบ 3 แกน (X, Y, Z) หรือส่งเฉพาะแกน X?
//
// 🐛 ปัญหา: dashboard (core/analysis.py) อ่านเฉพาะ AccX_CH0/1/2 เท่านั้น
//    ส่วน AccY/AccZ ถูกส่งขึ้นคลาวด์แล้วทิ้งเปล่า ๆ = กิน bandwidth 3 เท่า
//    และกินโควตาฟรี 10 GB/เดือน เร็วขึ้น 3 เท่าโดยไม่ได้ประโยชน์
//
// false = ส่งเฉพาะ AccX  (แนะนำ — ประหยัด bandwidth ~65%)
// true  = ส่งครบ 3 แกน   (ถ้าจะเอา Y/Z ไปวิเคราะห์เพิ่มในอนาคต)
//
// ⚠️ เปลี่ยนค่านี้แล้วต้องแฟลชบอร์ดใหม่ — dashboard ทำงานได้ทั้งสองแบบ
#define SEND_ALL_AXES  false

// ---------- การลบข้อมูลเก่า ----------
#define ENABLE_AUTO_CLEANUP  true
#define KEEP_SECONDS         60UL     // เก็บย้อนหลังกี่วินาที
#define CLEANUP_EVERY_MS     15000UL
#define CLEANUP_CHUNK        200      // ลบครั้งละไม่เกินกี่ key

// ---------- คาบงานประจำ ----------
#define HEARTBEAT_MS   5000UL
#define WATCHDOG_MS    10000UL
#define NVS_WRITE_MS   300000UL   // เขียน NVS ทุก 5 นาที (ถนอมอายุ flash)

// ---------- เกณฑ์ watchdog ----------
#define RSSI_MIN       -85
#define HEAP_MIN       30000

// ---------- NTP ----------
#define NTP_SERVER1    "pool.ntp.org"
#define NTP_SERVER2    "time.nist.gov"
#define GMT_OFFSET_SEC (7 * 3600)
#define DST_OFFSET_SEC 0
#define NTP_TIMEOUT_MS 20000
