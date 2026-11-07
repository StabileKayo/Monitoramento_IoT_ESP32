import socket
import threading

# Configuração Banco de dados

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "iot",
    "password" : "iot123",
    "database": "monitoramento_iot",
}

# Endereços e portas em que o gateway vai escutar cada protocolo
# 0.0.0.0 significa "aceita conexões em qualquer interface de rede"

UDP_HOST = "0.0.0.0"
UDP_PORT = 5001


def main():
    print("Gateway rodando. Pressione Ctrl+C para encerrar.")


if __name__ == "__main__":
    main()