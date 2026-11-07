// Nó real de monitoramento: ESP32 + DHT11 (temperatura e umidade do ar)
// + sensor capacitivo de umidade do solo.

#include <WiFi.h>
#include <DHT.h>
#include <time.h>
#include "secrets.h"


// Intervalo entre leituras (o DHT11 aceita no mínimo 1 leitura por segundo)
const unsigned long INTERVALO_MS = 10000;

// Pinos
#define PINO_DHT   4
#define TIPO_DHT   DHT11
#define PINO_SOLO  34   // precisa ser um pino ADC1 (32-39): o ADC2 não funciona com Wi-Fi ligado

// Calibração do sensor capacitivo de solo (valores brutos do ADC, 0 a 4095).
// Meça o seu: sensor no ar/seco -> VALOR_SECO; sensor na água -> VALOR_MOLHADO.
// Quanto MAIS úmido, MENOR o valor lido (característica do sensor capacitivo).
const int VALOR_SECO    = 3000;
const int VALOR_MOLHADO = 1300;

// Fuso horário do Brasil (UTC-3), usado para gerar o timestamp igual ao dos nós simulados
const long FUSO_SEGUNDOS = -3 * 3600;

DHT dht(PINO_DHT, TIPO_DHT);

unsigned long ultimoEnvio = 0;

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

void sincronizarRelogio() {
  // O ESP32 não tem relógio de verdade: pedimos a hora a servidores NTP pela internet.
  // Sem isso não teríamos como gerar o timestamp da leitura.
  configTime(FUSO_SEGUNDOS, 0, "pool.ntp.org", "time.google.com");
  struct tm info;
  if (getLocalTime(&info, 10000)) {
    Serial.println("Relógio sincronizado via NTP.");
  } else {
    // Não é fatal: o gateway preenche o timestamp com a hora dele
    Serial.println("Falha no NTP. Leituras seguirão sem timestamp (o gateway preenche).");
  }
}

// Escreve o timestamp no formato ISO 8601 ("2026-11-07T14:30:00"), igual ao dos simuladores.
// Retorna false se o relógio ainda não está sincronizado.
bool obterTimestamp(char* destino, size_t tamanho) {
  struct tm info;
  if (!getLocalTime(&info, 2000)) return false;
  strftime(destino, tamanho, "%Y-%m-%dT%H:%M:%S", &info);
  return true;
}

// Lê o solo várias vezes e tira a média, porque o ADC do ESP32 é bem ruidoso.
// Retorna a umidade em % (0 = seco, 100 = molhado).
float lerUmidadeSolo() {
  long soma = 0;
  const int AMOSTRAS = 10;
  for (int i = 0; i < AMOSTRAS; i++) {
    soma += analogRead(PINO_SOLO);
    delay(10);
  }
  int bruto = soma / AMOSTRAS;

  // Converte o valor bruto em porcentagem (invertido: valor alto = seco)
  float pct = (float)(VALOR_SECO - bruto) * 100.0 / (float)(VALOR_SECO - VALOR_MOLHADO);
  pct = constrain(pct, 0.0, 100.0);

  // Mostra o valor bruto no Serial: útil para calibrar VALOR_SECO e VALOR_MOLHADO
  Serial.printf("Solo bruto (ADC): %d -> %.1f%%\n", bruto, pct);
  return pct;
}

void setup() {
  Serial.begin(115200);
  delay(500);
  dht.begin();
  analogReadResolution(12);                     // 0 a 4095
  analogSetPinAttenuation(PINO_SOLO, ADC_11db); // faixa de ~0 a 3,3V
  conectarWifi();
  sincronizarRelogio();
}

void loop() {
  // millis() em vez de delay(): o loop continua livre e o intervalo não acumula atraso
  if (millis() - ultimoEnvio < INTERVALO_MS) return;
  ultimoEnvio = millis();

  float temperatura = dht.readTemperature();   // °C
  float umidadeAr   = dht.readHumidity();      // %
  float umidadeSolo = lerUmidadeSolo();        // %

  if (isnan(temperatura) || isnan(umidadeAr)) {
    Serial.println("Falha ao ler o DHT11 (confira ligação e pull-up).");
  }

  Serial.printf("Temperatura: %.1f C | Ar: %.1f %% | Solo: %.1f %%\n", temperatura, umidadeAr, umidadeSolo);
  char ts[24];
  if (obterTimestamp(ts, sizeof(ts))) Serial.printf("Timestamp: %s\n", ts);
}