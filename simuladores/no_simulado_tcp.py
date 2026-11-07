import random
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


def main():
    valores = valor_inicial()
    print(f"[{NO_ID}] Valores iniciais: {valores}")

    for _ in range(3):
        valores = variar(valores)
        print(f"[{NO_ID}] Novo valor simulado: {valores}")


if __name__ == "__main__":
    main()