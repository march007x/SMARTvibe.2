// ============================================================
//  sensors.h — อ่าน MPU6050 x3 ผ่าน TCA9548A multiplexer
//  โมดูลนี้ไม่รู้จัก WiFi/Firebase เลย ทดสอบแยกได้
// ============================================================
#pragma once
#include <Arduino.h>
#include "types.h"

// เริ่มต้น I2C + calibrate gyro ทั้ง 3 ตัว (ใช้เวลา ~10 วินาที)
// วางบอร์ดนิ่ง ๆ ระหว่าง calibrate
bool sensorsBegin();

// อ่านค่าครบทั้ง 3 ชั้น ใส่ลง out (ยังไม่ใส่ epoch_ms)
// คืน false ถ้าจับ mutex ของ I2C ไม่ได้ภายใน timeoutMs
bool sensorsRead(Sample_t &out, uint32_t timeoutMs = 10);

// สแกนหาอุปกรณ์บนบัส I2C ทุกช่องของ TCA — ใช้ตอน debug สายหลุด
void sensorsScan();
