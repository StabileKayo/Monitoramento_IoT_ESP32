// Nó real de monitoramento: ESP32 + DHT11 (temperatura e umidade do ar)
// + sensor capacitivo de umidade do solo.

#include <WiFi.h>
#include "secrets.h"

void conectarWifi() {
  Serial.printf("Conectando ao Wi-Fi '%s'", WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_SENHA);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.printf("\nConectado! IP do ESP32: %s\n",
                WiFi.localIP().toString().c_str());
}

void setup() {
  Serial.begin(115200);
  delay(500);
  conectarWifi();
}

void loop() {
  // por enquanto não faz nada
}