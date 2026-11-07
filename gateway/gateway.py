import socket
import threading

import mariadb
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


def conectar_banco():
    # Abre uma nova conexão com o banco de dados. Cada thread chama isso uma vez,
    return mariadb.connect(**DB_CONFIG)


def salvar_leituras(conexao, mensagem: dict):
    # Insere uma leitura na tabela "leituras". Usa .get() em vez de acesso direto
    # para não quebrar caso algum campo venha faltando na mensagem
    sql = """
        INSERT INTO leituras
            (no_id, protocolo, timestamp_no, temperatura, umidade_ar, umidade_solo)
        VALUES
            (?, ?, ?, ?, ?, ?)
    """

    valores = (
        mensagem.get("no_id"),
        mensagem.get("protocolo"),
        mensagem.get("timestamp"),
        mensagem.get("temperatura"),
        mensagem.get("umidade_ar"),
        mensagem.get("umidade_solo")
    )
    cursor = conexao.cursor()
    cursor.execute(sql, valores)
    conexao.commit()
    cursor.close()


def main():
    print("Gateway rodando. Pressione Ctrl+C para encerrar.")


if __name__ == "__main__":
    main()