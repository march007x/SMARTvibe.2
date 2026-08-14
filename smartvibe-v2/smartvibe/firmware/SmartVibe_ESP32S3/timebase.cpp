#include "timebase.h"
#include "config.h"
#include <time.h>
#include <sys/time.h>

bool timebaseBegin() {
  configTime(GMT_OFFSET_SEC, DST_OFFSET_SEC, NTP_SERVER1, NTP_SERVER2);
  uint32_t t0 = millis();
  while (millis() - t0 < NTP_TIMEOUT_MS) {
    // > 1700000000 = หลัง พ.ย. 2023 แปลว่า sync สำเร็จแล้ว
    if (time(nullptr) > 1700000000) return true;
    delay(250);
    Serial.print(".");
  }
  return false;
}

uint64_t epochMillis() {
  struct timeval tv;
  gettimeofday(&tv, nullptr);
  return (uint64_t)tv.tv_sec * 1000ULL + (uint64_t)(tv.tv_usec / 1000);
}

uint64_t quantize(uint64_t ms) {
  return (ms / KEY_STEP_MS) * KEY_STEP_MS;
}

String keyOf(uint64_t ms) {
  char buf[16];
  snprintf(buf, sizeof(buf), "%013llu", (unsigned long long)ms);
  return String(buf);
}
