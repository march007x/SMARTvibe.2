// ============================================================
//  SmartVibe — ระบบเฝ้าระวังความเสียหายโครงสร้างอาคารจำลอง 3 ชั้น
//  บอร์ด: ESP32-S3 N16R8   |   เซ็นเซอร์: MPU-6050 x3 ผ่าน TCA9548A
//
//  ไฟล์นี้ทำหน้าที่ "ประกอบร่าง" อย่างเดียว ตรรกะจริงอยู่ในโมดูล:
//    config.h    — ค่าคงที่ทั้งหมด (แก้ค่าที่นี่)
//    secrets.h   — WiFi / Firebase (คุณต้องสร้างเอง ดู secrets.h.example)
//    types.h     — โครงสร้างข้อมูล
//    timebase.*  — NTP + การสร้าง key
//    sensors.*   — อ่าน MPU6050 x3
//    uploader.*  — คุยกับ Firebase
//    tasks.*     — แยก sampler / uploader คนละคอร์
// ============================================================

#include "config.h"
#include "timebase.h"
#include "sensors.h"
#include "uploader.h"
#include "tasks.h"

void setup() {
  Serial.begin(115200);
  delay(2000);                 // รอ USB CDC ของ S3 พร้อม
  Serial.println("\n===== SmartVibe =====");

  if (!sensorsBegin()) { Serial.println("❌ เซ็นเซอร์ล้มเหลว"); ESP.restart(); }
  sensorsScan();               // แสดงผลสแกน I2C ไว้ debug สายหลุด

  if (!uploaderBegin()) { Serial.println("❌ เครือข่ายล้มเหลว"); ESP.restart(); }

  Serial.print("sync NTP");
  if (!timebaseBegin()) {
    // ต้อง restart เพราะถ้าไม่มี NTP key จะกลับไปเป็นเลขเล็กเหมือนบั๊กเดิม
    Serial.println("\n❌ NTP ล้มเหลว → restart");
    delay(2000);
    ESP.restart();
  }
  Serial.printf("\n✅ NTP ok — epoch_ms = %s\n", keyOf(epochMillis()).c_str());

  if (!tasksBegin()) ESP.restart();
  Serial.println("✅ SmartVibe พร้อมทำงาน\n");
}

void loop() {
  vTaskDelay(pdMS_TO_TICKS(1000));   // งานจริงอยู่ใน FreeRTOS task ทั้งหมด
}
