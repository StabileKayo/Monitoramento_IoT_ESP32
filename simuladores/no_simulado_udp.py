# Configuração

GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 5001
NO_ID = "simulado_udp_b"
INTERVALO_SEGUNDOS = 10


def main():
    print(f"[{NO_ID}] Simulador de nó sensor (UDP) - configuração carregada")
    print(f"Destino: {GATEWAY_HOST}:{GATEWAY_PORT}")


if __name__ == "__main__":
    main()