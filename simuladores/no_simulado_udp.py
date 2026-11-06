import random

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


def main():
    valores = valor_inicial()

    print(f"[{NO_ID}] Valores iniciais: {valores}")

    # Teste temporário: gera algumas variações só para validar a lógica
    for _ in range(3):
        valores = variar(valores)
        print(f"[{NO_ID}] Novo valor simulado: {valores}")


if __name__ == "__main__":
    main()