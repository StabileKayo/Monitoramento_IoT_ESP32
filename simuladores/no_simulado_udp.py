import json
import random
from datetime import datetime

# Configuração BD

GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 5001
NO_ID = "simulado_udp_b"
INTERVALO_SEGUNDOS = 10

# Faixa (minimo, maximo) que cada grandeza pode assumir,
# simulando limite físicos reais dos sensores (temperatura, umidade do ar e do solo)
FAIXAS = {
    "temperatura": (16.0, 35.0),
    "umidade_ar": (30.0, 80.0),
    "umidade_solo": (15.0, 70.0),
}


def valor_inicial():
    # Sorteia um valor de partida dentro da faixa de cada grandeza
    return {chave: random.uniform(*faixa) for chave,faixa in FAIXAS.items()}


def variar(valores):
    # Em vez de sortear valores totalmente novos a cada leitura,
    # aplica uma pequena variação sobre o valor anterior
    novos = {}
    for chave, (minimo, maximo) in FAIXAS.items():
        passo = random.uniform(-0.6, 0.6)
        novo_valor = valores[chave] + passo
        # Garante que o valor nunca ultrapasse os limites físicos definidos
        novo_valor = max(minimo, min(maximo,novo_valor))
        novos[chave] = round(novo_valor, 1)
    return novos


def montar_mensagem(valores):
    # Monta o pacote que será enviado ao gateway: identificação do nó,
    # protocolo usado e o momento exato da leitura, além dos valores dos sensores
    mensagem = {
        "no_id": NO_ID,
        "protocolo": "UDP",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    mensagem.update(valores)
    return mensagem


def main():
    valores = valor_inicial()

    # Teste temporário: gera algumas variações só para validar a lógica
    for _ in range(3):
        valores = variar(valores)
        mensagem = montar_mensagem(valores)
        print(f"[{NO_ID}] Mensagem montada: {mensagem}")

if __name__ == "__main__":
    main()