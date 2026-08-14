#include "uploader.h"
#include "config.h"
#include "secrets.h"
#include "timebase.h"

#include <WiFi.h>
#include <Preferences.h>
#include <Firebase_ESP_Client.h>
#include <addons/TokenHelper.h>
#include <addons/RTDBHelper.h>

Stats_t g_stats = {0, 0, 0};

static FirebaseData   fbdo;      // สำหรับข้อมูลหลัก
static FirebaseData   fbdoMeta;  // แยก object กัน SSL session ชนกัน
static FirebaseAuth   auth;
static FirebaseConfig config;
static Preferences    prefs;
static uint64_t       g_lastCleanupKey = 0;

// ------------------------------------------------------------
bool uploaderBegin() {
  prefs.begin("smartvibe", false);
  g_lastCleanupKey = prefs.getULong64("cleanKey", 0);

  Serial.print("เชื่อมต่อ WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);            // ปิด power save → latency นิ่งขึ้นมาก
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
    if (millis() - t0 > 30000) { Serial.println("\n❌ ต่อ WiFi ไม่ได้"); return false; }
  }
  Serial.printf("\n✅ WiFi IP: %s  RSSI: %d dBm\n",
                WiFi.localIP().toString().c_str(), WiFi.RSSI());

  config.host = FIREBASE_HOST;
  config.signer.tokens.legacy_token = FIREBASE_AUTH;
  config.timeout.serverResponse   = 8000;
  config.timeout.socketConnection = 8000;
  config.timeout.wifiReconnect    = 10000;

  // =================================================================
  // 🎯 จุดสำคัญ: ต้องกำหนด Buffer Size (16384) "ก่อน" สั่ง Firebase.begin()
  // =================================================================
  fbdo.setBSSLBufferSize(16384, 1024);
  fbdo.setResponseSize(2048);

  fbdoMeta.setBSSLBufferSize(16384, 1024);
  fbdoMeta.setResponseSize(2048);

  // เริ่มต้นเชื่อมต่อ Firebase หลังจากตั้งค่า Buffer แล้ว
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);

  Serial.printf("📡 DB: %s\n📂 path: %s\n", FIREBASE_HOST, DB_PATH);
  return true;
}

// ------------------------------------------------------------
bool uploaderSendBatch(const Batch_t &b) {
  if (!Firebase.ready()) {
    g_stats.failed += b.n;
    Serial.println("⏸️  Firebase ยังไม่พร้อม");
    return false;
  }

  FirebaseJson batchJson;
  for (uint16_t i = 0; i < b.n; i++) {
    FirebaseJson rec;
    // ส่ง epoch_ms เป็น string กันปัญหา double ปัดเลข 13 หลัก
    rec.set("uptime_ms", keyOf(b.s[i].epoch_ms));
    rec.set("AccX_CH0", b.s[i].ax[0]);
    rec.set("AccX_CH1", b.s[i].ax[1]);
    rec.set("AccX_CH2", b.s[i].ax[2]);
#if SEND_ALL_AXES
    // ตั้ง SEND_ALL_AXES เป็น true ใน config.h ถ้าจะเอา Y/Z ไปใช้ด้วย
    rec.set("AccY_CH0", b.s[i].ay[0]);
    rec.set("AccZ_CH0", b.s[i].az[0]);
    rec.set("AccY_CH1", b.s[i].ay[1]);
    rec.set("AccZ_CH1", b.s[i].az[1]);
    rec.set("AccY_CH2", b.s[i].ay[2]);
    rec.set("AccZ_CH2", b.s[i].az[2]);
#endif
    batchJson.set(keyOf(b.s[i].epoch_ms), rec);
  }

  uint32_t t0 = millis();
  if (Firebase.RTDB.updateNode(&fbdo, DB_PATH, &batchJson)) {
    g_stats.sent += b.n;
    Serial.printf("🚀 [OK] n=%u | %lums | heap=%u | rssi=%d\n",
                  b.n, millis() - t0, ESP.getFreeHeap(), WiFi.RSSI());
    return true;
  }

  g_stats.failed += b.n;
  Serial.printf("❌ [FAIL] http=%d | %s | rssi=%d | heap=%u\n",
                fbdo.httpCode(), fbdo.errorReason().c_str(),
                WiFi.RSSI(), ESP.getFreeHeap());
  return false;
}

// ------------------------------------------------------------
void uploaderCleanup() {
  if (!ENABLE_AUTO_CLEANUP || !Firebase.ready()) return;

  uint64_t cutoff = quantize(epochMillis() - KEEP_SECONDS * 1000ULL);
  uint64_t from   = g_lastCleanupKey;

  // ถ้าไม่เคยลบ หรือค้างมานานเกินไป ให้เริ่มไล่จากจุดที่สมเหตุสมผล
  if (from == 0 || from + KEEP_SECONDS * 4000ULL < cutoff) {
    from = cutoff - KEEP_SECONDS * 2000ULL;
  }
  from = quantize(from);
  if (from >= cutoff) return;

  String payload = "{";
  int count = 0;
  for (uint64_t k = from; k < cutoff && count < CLEANUP_CHUNK; k += KEY_STEP_MS) {
    if (count) payload += ",";
    payload += "\"" + keyOf(k) + "\":null";
    count++;
    g_lastCleanupKey = k + KEY_STEP_MS;
  }
  payload += "}";
  if (count == 0) return;

  FirebaseJson delJson;
  delJson.setJsonData(payload);

  if (Firebase.RTDB.updateNode(&fbdoMeta, DB_PATH, &delJson)) {
    static uint32_t lastNvs = 0;
    if (lastNvs == 0 || millis() - lastNvs > NVS_WRITE_MS) {
      prefs.putULong64("cleanKey", g_lastCleanupKey);
      lastNvs = millis();
    }
    Serial.printf("🗑️  cleanup %d keys → %llu\n",
                  count, (unsigned long long)g_lastCleanupKey);
  } else {
    Serial.printf("⚠️  cleanup fail http=%d | %s\n",
                  fbdoMeta.httpCode(), fbdoMeta.errorReason().c_str());
  }
}

// ------------------------------------------------------------
void uploaderHeartbeat() {
  if (!Firebase.ready()) return;

  // ให้เซิร์ฟเวอร์ประทับเวลาเอง — วิธีนี้เชื่อถือได้กว่า .sv ใน FirebaseJson
  Firebase.RTDB.setTimestamp(&fbdoMeta, META_PATH "/heartbeat/server_ts");

  FirebaseJson hb;
  hb.set("device_epoch", keyOf(epochMillis()));
  hb.set("rssi",       WiFi.RSSI());
  hb.set("free_heap", (int)ESP.getFreeHeap());
  hb.set("sent",       (int)g_stats.sent);
  hb.set("failed",     (int)g_stats.failed);
  hb.set("dropped",    (int)g_stats.dropped);

  if (!Firebase.RTDB.updateNode(&fbdoMeta, META_PATH "/heartbeat", &hb)) {
    Serial.printf("⚠️  heartbeat fail http=%d | %s\n",
                  fbdoMeta.httpCode(), fbdoMeta.errorReason().c_str());
  }
}

// ------------------------------------------------------------
void uploaderWatchdog() {
  int rssi = WiFi.RSSI();
  if (WiFi.status() != WL_CONNECTED || rssi == 0 || rssi < RSSI_MIN) {
    Serial.printf("📶 สัญญาณผิดปกติ (status=%d rssi=%d) → reconnect\n",
                  WiFi.status(), rssi);
    WiFi.disconnect();
    delay(100);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  }
  if (ESP.getFreeHeap() < HEAP_MIN) {
    Serial.println("💥 heap ต่ำมาก → restart");
    delay(200);
    ESP.restart();
  }
}