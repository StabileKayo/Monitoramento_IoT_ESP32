import json
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

TCP_HOST = "0.0.0.0"
TCP_PORT = 5000
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


def processar_mensagem(protocolo_esperado, linha_bytes, conexao, origem=""):
    # Faz o parse do JSON recebido e grava no banco, tratando erros sem derrumar o listener inteiro
    # Um pacote inválido de um nó não pode travar o recebimento dos demais
    try:
        mensagem = json.loads(linha_bytes.decode("utf-8"))
        salvar_leituras(conexao, mensagem)
        print(f"[{protocolo_esperado}{origem}] Gravado: {mensagem}")
    except json.JSONDecodeError:
        # Pacote corrompido ou não-JSON: registra e segue em frente
        print(f"[{protocolo_esperado}{origem}] Mensagem inválida (não era JSON): {linha_bytes!r}")
    except mariadb.Error as erro:
        # Falha no banco (conexão caiu, tabela errada, etc): registra sem derrubar o listener
        print(f"[{protocolo_esperado}{origem}] Erro ao gravar no banco de dados: {erro}")


def escutar_udp():
    conexao_db = conectar_banco()
    servidor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    servidor.bind((UDP_HOST, UDP_PORT))
    print(f"[UDP] Escutando em {UDP_HOST}:{UDP_PORT}")

    # UDP não tem conceito de "conexão" cada datagrama é uma mensagem completa e independente
    # então basta receber e processar em loop
    while True:
        dados, endereco = servidor.recvfrom(1024)
        processar_mensagem("UDP", dados, conexao_db, origem=f" {endereco}")


def tratar_cliente_tcp(conn_socket, endereco, conexao_db):
    print(f"[TCP] Novo nó conectado: {endereco}")
    buffer = b""
    with conn_socket:
        while True:
            dados = conn_socket.recv(1024)
            if not dados:
                print(f"[TCP] no {endereco} desconectou.")
                break
            # TCP é um fluxo continuo de bytes, sem limites de mensagem:
            # por isso acumulamos num buffer e so processamos quando
            # encontramos o delimitador \n que marca o fim de uma leitura

            buffer += dados
            while b"\n" in buffer:
                linha, buffer = buffer.split(b"\n", 1)
                if linha.strip():
                    processar_mensagem("TCP", linha, conexao_db, origem=f" {endereco}")


def escutar_tcp():
    conexao_db = conectar_banco()
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permite reiniciar o gateway rapidamente sem esperar a porta ser liberada pelo SO
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((TCP_HOST, TCP_PORT))
    servidor.listen()
    print(f"[TCP] Escutando em {TCP_HOST}:{TCP_PORT}")

    while True:
        conn_socket, endereco = servidor.accept()
        # Trata um nó TCP de cada vez nesta thread, mantendo simples por ora
        # (multiplos nós TCP simultaneos serão resolvidos com threading)
        tratar_cliente_tcp(conn_socket, endereco, conexao_db)


def main():
    # Cada listener roda em sua própria thrad, como daemon, para que
    # o programa principal encerre ambos ao sair (Ctrl+C)
    thread_tcp = threading.Thread(target=escutar_tcp, daemon=True)
    thread_udp = threading.Thread(target=escutar_udp, daemon=True)

    thread_tcp.start()
    thread_udp.start()

    print("Gateway rodando. Pressione Ctrl+C para encerrar.")
    try:
        # Mantem a thread principal viva enquanto as threads daemon trabalham
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\nGateway encerrado.")


if __name__ == "__main__":
    main()