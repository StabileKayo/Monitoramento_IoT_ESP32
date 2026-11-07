# Configuração banco de dados

GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 5000
NO_ID = "simulado_tcp_a"
INTERVALO_SEGUNDOS = 15


def main():
    print(f"[{NO_ID}] Simulador de nó sensor (TCP) - Configuração carregada")
    print(f"Destino: {GATEWAY_HOST}:{GATEWAY_PORT}")


if __name__ == "__main__":
    main()