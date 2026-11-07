// Nó real de monitoramento: ESP32 + DHT11 (temperatura e umidade do ar)
// + sensor capacitivo de umidade do solo.

#include <WiFi.h>
#include <DHT.h>
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

// Intervalo entre leituras (o DHT11 aceita no mínimo 1 leitura por segundo)
const unsigned long INTERVALO_MS = 10000;

// Pinos
#define PINO_DHT   4
#define TIPO_DHT   DHT11

DHT dht(PINO_DHT, TIPO_DHT);

unsigned long ultimoEnvio = 0;
void setup() {
  Serial.begin(115200);
  delay(500);
  dht.begin();
  conectarWifi();
}

void loop() {
  // millis() em vez de delay(): o loop continua livre e o intervalo não acumula atraso
  if (millis() - ultimoEnvio < INTERVALO_MS) return;
  ultimoEnvio = millis();

  float temperatura = dht.readTemperature();   // °C
  float umidadeAr   = dht.readHumidity();      // %

  if (isnan(temperatura) || isnan(umidadeAr)) {
    Serial.println("Falha ao ler o DHT11 (confira ligação e pull-up).");
  }

  Serial.printf("Temperatura: %.1f C | Umidade do ar: %.1f %%\n", temperatura, umidadeAr);
}