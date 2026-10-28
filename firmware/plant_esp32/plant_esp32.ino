// Plant Whisperer - ESP32 firmware (Arduino IDE)
// Libraries: "DHT sensor library" + "Adafruit Unified Sensor"
#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASS = "YOUR_PASSWORD";
const char* SERVER    = "http://192.168.1.50:5000/reading";  // your laptop's IP

#define SOIL_PIN 34   // soil sensor AO
#define LDR_PIN  35   // LDR divider midpoint
#define DHT_PIN  4    // DHT11 data
DHT dht(DHT_PIN, DHT11);

int avgRead(int pin) {
  long s = 0;
  for (int i = 0; i < 10; i++) { s += analogRead(pin); delay(10); }
  return s / 10;
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\nConnected: " + WiFi.localIP().toString());
}

void loop() {
  int soil = avgRead(SOIL_PIN);
  int ldr  = avgRead(LDR_PIN);
  float t = dht.readTemperature();
  float h = dht.readHumidity();

  if (!isnan(t) && !isnan(h)) {
    String body = "{\"soil_raw\":" + String(soil) + ",\"ldr_raw\":" + String(ldr) +
                  ",\"temp\":" + String(t, 1) + ",\"hum\":" + String(h, 1) + "}";
    HTTPClient http;
    http.begin(SERVER);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST(body);
    Serial.println(body + " -> " + String(code));
    http.end();
  } else {
    Serial.println("DHT read failed");
  }
  delay(30000);  // every 30 s (use 5000 while testing)
}
