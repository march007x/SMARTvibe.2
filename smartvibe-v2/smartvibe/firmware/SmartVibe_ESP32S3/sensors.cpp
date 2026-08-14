#include "sensors.h"
#include "config.h"
#include <Wire.h>
#include <MPU6050_tockn.h>

static MPU6050 mpu[N_FLOORS] = { MPU6050(Wire), MPU6050(Wire), MPU6050(Wire) };
static const uint8_t CHAN[N_FLOORS] = { CH_FLOOR1, CH_FLOOR2, CH_FLOOR3 };
static SemaphoreHandle_t i2cMutex = nullptr;

static void tcaselect(uint8_t channel) {
  if (channel > 7) return;
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << channel);
  Wire.endTransmission();
}

bool sensorsBegin() {
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(I2C_FREQ);

  i2cMutex = xSemaphoreCreateMutex();
  if (!i2cMutex) return false;

  for (int i = 0; i < N_FLOORS; i++) {
    Serial.printf("ตั้งค่าเซ็นเซอร์ชั้น %d (CH%d)...\n", i + 1, CHAN[i]);
    tcaselect(CHAN[i]);
    mpu[i].begin();
    mpu[i].calcGyroOffsets(true);   // ต้องวางบอร์ดนิ่ง
  }
  Serial.println("\n✅ MPU6050 x3 พร้อมใช้งาน");
  return true;
}

bool sensorsRead(Sample_t &out, uint32_t timeoutMs) {
  if (xSemaphoreTake(i2cMutex, pdMS_TO_TICKS(timeoutMs)) != pdTRUE) return false;
  for (int i = 0; i < N_FLOORS; i++) {
    tcaselect(CHAN[i]);
    mpu[i].update();
    out.ax[i] = mpu[i].getAccX();
    out.ay[i] = mpu[i].getAccY();
    out.az[i] = mpu[i].getAccZ();
  }
  xSemaphoreGive(i2cMutex);
  return true;
}

void sensorsScan() {
  for (int c = 0; c < N_FLOORS; c++) {
    tcaselect(CHAN[c]);
    Serial.printf("CH%d: ", CHAN[c]);
    int found = 0;
    for (uint8_t a = 1; a < 127; a++) {
      Wire.beginTransmission(a);
      if (Wire.endTransmission() == 0) { Serial.printf("0x%02X ", a); found++; }
    }
    Serial.println(found ? "" : "❌ ไม่พบอุปกรณ์ — ตรวจสายช่องนี้");
  }
}
