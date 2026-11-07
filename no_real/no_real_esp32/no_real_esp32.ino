// Nó real de monitoramento: ESP32 + DHT11 (temperatura e umidade do ar)
// + sensor capacitivo de umidade do solo.

#include <WiFi.h>
#include <WiFiUdp.h>
#include <DHT.h>
#include <time.h>
#include "secrets.h"


// Intervalo entre leituras (o DHT11 aceita no mínimo 1 leitura por segundo)
const unsigned long INTERVALO_MS = 10000;

// Pinos
#define PINO_DHT   4
#define TIPO_DHT   DHT11
#define PINO_SOLO  34   // precisa ser um pino ADC1 (32-39): o ADC2 não funciona com Wi-Fi ligado

// IP do computador que roda o gateway, na mesma rede do ESP32.
// NÃO use 127.0.0.1: para o ESP32 isso seria ele mesmo.
// (no Windows: ipconfig | no Linux/macOS: ip a ou ifconfig)

const uint16_t GATEWAY_PORTA_TCP = 5000;
const uint16_t GATEWAY_PORTA_UDP = 5001;

// Escolha o protocolo de envio: true = TCP, false = UDP
const bool USAR_TCP = true;

const char* NO_ID = "esp32_real";

// Calibração do sensor capacitivo de solo (valores brutos do ADC, 0 a 4095).
// Meça o seu: sensor no ar/seco -> VALOR_SECO; sensor na água -> VALOR_MOLHADO.
// Quanto MAIS úmido, MENOR o valor lido (característica do sensor capacitivo).
const int VALOR_SECO    = 3000;
const int VALOR_MOLHADO = 1300;

// Fuso horário do Brasil (UTC-3), usado para gerar o timestamp igual ao dos nós simulados
const long FUSO_SEGUNDOS = -3 * 3600;

DHT dht(PINO_DHT, TIPO_DHT);
WiFiClient clienteTcp;
WiFiUDP udp;

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
// Converte float em texto para o JSON. NaN (leitura que falhou) vira "null",
// que o gateway grava como NULL no banco em vez de perder a leitura toda.

void formatarValor(float valor, char* destino, size_t tamanho) {
  if (isnan(valor)) {
    snprintf(destino, tamanho, "null");
  } else {
    snprintf(destino, tamanho, "%.1f", valor);
  }
}

bool enviarTcp(const char* json) {
  // Se a conexão caiu (ou ainda não existe), tenta reconectar antes de enviar
  if (!clienteTcp.connected()) {
    clienteTcp.stop();
    Serial.println("Conectando ao gateway (TCP)...");
    if (!clienteTcp.connect(GATEWAY_HOST, GATEWAY_PORTA_TCP)) {
      Serial.println("Gateway TCP indisponível.");
      return false;
    }
  }
  // O "\n" ao final é o delimitador que o gateway usa para separar as mensagens
  clienteTcp.print(json);
  clienteTcp.print("\n");
  return true;
}

bool enviarUdp(const char* json) {
  // UDP não tem conexão nem confirmação: cada leitura é um datagrama avulso
  udp.beginPacket(GATEWAY_HOST, GATEWAY_PORTA_UDP);
  udp.print(json);
  return udp.endPacket() == 1;
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

  // 1) Lê os sensores
  float temperatura = dht.readTemperature();   // °C
  float umidadeAr   = dht.readHumidity();      // %
  float umidadeSolo = lerUmidadeSolo();        // %

  if (isnan(temperatura) || isnan(umidadeAr)) {
    Serial.println("Falha ao ler o DHT11 (confira ligação e pull-up).");
  }

  // 2) Monta o JSON (mesmo formato dos nós simulados), sem depender de bibliotecas extras
  char tsCampo[48] = "";
  char ts[24];
  if (obterTimestamp(ts, sizeof(ts))) {
    snprintf(tsCampo, sizeof(tsCampo), "\"timestamp\":\"%s\",", ts);
  }

  char t[12], ua[12], us[12];
  formatarValor(temperatura, t, sizeof(t));
  formatarValor(umidadeAr, ua, sizeof(ua));
  formatarValor(umidadeSolo, us, sizeof(us));

  char json[256];
  snprintf(json, sizeof(json),
           "{\"no_id\":\"%s\",\"protocolo\":\"%s\",%s\"temperatura\":%s,\"umidade_ar\":%s,\"umidade_solo\":%s}",
           NO_ID, USAR_TCP ? "TCP" : "UDP", tsCampo, t, ua, us);

  // 3) Envia ao gateway
  bool ok = USAR_TCP ? enviarTcp(json) : enviarUdp(json);
  Serial.printf("%s: %s\n", ok ? "Enviado" : "FALHA ao enviar", json);
}