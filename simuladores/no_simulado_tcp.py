import json
import random
import socket
from datetime import datetime
import time
# Configuração banco de dados

GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 5000
NO_ID = "simulado_tcp_a"
INTERVALO_SEGUNDOS = 15


# Faixas realistas para partir e para o "passeio aleatório" não sair delas
FAIXAS = {
    "temperatura": (16.0, 35.0),
    "umidade_ar": (30.0, 80.0),
    "umidade_solo": (15.0, 70.0),
}


def valor_inicial():
    # Sorteia um valor de partida dentro da faixa de cada grandeza
    return {chave: random.uniform(*faixa) for chave, faixa in FAIXAS.items()}


def variar(valores):
    # Faz cada leitura variar um pouco em relação a anterior
    novos = {}
    for chave, (minimo, maximo) in FAIXAS.items():
        passo = random.uniform(-0.6, 0.6)
        novo_valor = valores[chave] + passo
        novo_valor = max(minimo, min(maximo, novo_valor))
        novos[chave] = round(novo_valor, 1)
    return novos


def montar_mensagem(valores):
    mensagem = {
        "no_id": NO_ID,
        "protocolo": "TCP",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    mensagem.update(valores)
    return mensagem


def conectar():
    # Tenta conectar ao gateway, com nova tentativa a cada 3s se falhar
    # Isso permite ligar o simulador antes mesmo do gateway estar de pé
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((GATEWAY_HOST, GATEWAY_PORT))
            print(f"[{NO_ID}] Conectado ao gateway em {GATEWAY_HOST}:{GATEWAY_PORT}")
            return sock
        except (ConnectionRefusedError, OSError) as erro:
            print(f"[{NO_ID}] Gateway indisponivel ({erro}). Tentando novamente em 3s...")
            time.sleep(3)


def main():
    sock =conectar()
    print(f"[{NO_ID}] Conexão estabelecida, pronta para enviar leituras")


if __name__ == "__main__":
    main()