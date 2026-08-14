// ============================================================
//  uploader.h — ทุกอย่างที่คุยกับ Firebase
//  แยกออกมาเพื่อให้ sensors/tasks ไม่ต้องรู้จัก Firebase เลย
// ============================================================
#pragma once
#include <Arduino.h>
#include "types.h"

// เชื่อมต่อ WiFi + Firebase (เรียกหลัง timebaseBegin())
bool uploaderBegin();

// ส่ง 1 batch ขึ้น Firebase — คืน false พร้อม log ละเอียดถ้าล้มเหลว
bool uploaderSendBatch(const Batch_t &b);

// ลบ key ที่เก่ากว่า KEEP_SECONDS โดยสร้าง raw JSON {"key":null,...}
//
// ⚠️ ของเดิมใช้ delJson.set(key) เฉย ๆ แล้วไม่เช็ค return value
// ทำให้ถ้าลบพลาดก็ไม่มีใครรู้ ที่นี่เช็คทั้ง return และ httpCode
void uploaderCleanup();

// เขียน /History3F_meta/heartbeat พร้อม server timestamp
//
// 🔍 ใช้ debug ปัญหา "Serial ขึ้น OK แต่ Firebase ไม่มีข้อมูล":
//    ถ้า server_ts ไม่ขยับ = SDK รายงาน success ปลอมจริง
//    ถ้า server_ts ขยับ = ปัญหาอยู่ที่ query ฝั่ง dashboard ไม่ใช่บอร์ด
void uploaderHeartbeat();

// ตรวจ WiFi/RSSI/heap แล้วซ่อมตัวเองถ้าผิดปกติ
void uploaderWatchdog();

extern Stats_t g_stats;
