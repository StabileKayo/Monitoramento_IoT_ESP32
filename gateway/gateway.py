import json
import socket
import threading
from datetime import datetime
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

# Se um nó TCP ficar tanto tempo sem enviar nada, consideramos a conexão morta
TCP_TIMEOUT_SEGUNDOS = 120

# Valor mínimo aceitável de cada grandeza. Abaixo disso, dispara alerta
LIMITES_MINIMOS = {
    "temperatura": 18.0,
    "umidade_ar": 35.0,
    "umidade_solo": 25.0,
}


def conectar_banco():
    # Abre uma nova conexão com o banco de dados. Cada thread chama isso uma vez,
    return mariadb.connect(**DB_CONFIG)


def salvar_leituras(conexao, mensagem: dict):
    # Insere uma leitura na tabela "leituras". Usa .get() em vez de acesso direto
    # para não quebrar caso algum campo venha faltando na mensagem
    if not isinstance(mensagem, dict) or not mensagem.get("no_id"):
        raise ValueError("mensagem sem no_id")

    # O ESP32 pode não ter conseguido sincronizar o relógio via NTP e enviar sem
    # timestamp. Nesse caso usamos a hora do gateway, para não perder a leitura
    # (a coluna timestamp_no é NOT NULL)
    timestamp = mensagem.get("timestamp") or datetime.now().isoformat(timespec="seconds")

    sql = """
        INSERT INTO leituras
            (no_id, protocolo, timestamp_no, temperatura, umidade_ar, umidade_solo)
        VALUES
            (?, ?, ?, ?, ?, ?)
    """

    valores = (
        mensagem.get("no_id"),
        mensagem.get("protocolo"),
        timestamp,
        mensagem.get("temperatura"),   # None (null no JSON) vira NULL no banco
        mensagem.get("umidade_ar"),
        mensagem.get("umidade_solo"),
    )
    cursor = conexao.cursor()
    try:
        cursor.execute(sql, valores)
        conexao.commit()
    finally:
        cursor.close()


def verificar_limites(mensagem: dict):
    # Compara cada grandeza com o seu limite mínimo
    # Retorna (baixas, normais): baixas = {grandeza: valor} abaixo do limite,
    # normais = lista de grandezas dentro do limite
    baixas = {}
    normais = []
    for grandeza, minimo in LIMITES_MINIMOS.items():
        valor = mensagem.get(grandeza)
        # None (null no JSON) significa que o sensor falhou: não é nem baixo nem normal,
        # então ignoramos para não abrir nem fechar alertas por engano
        if not isinstance(valor, (int, float)):
            continue
        if valor < minimo:
            baixas[grandeza] = valor
        else:
            normais.append(grandeza)
    return baixas, normais


def processar_mensagem(protocolo_esperado, linha_bytes, conexao, origem=""):
    # Faz o parse do JSON recebido e grava no banco, tratando erros sem derrumar o listener inteiro
    # Um pacote inválido de um nó não pode travar o recebimento dos demais
    try:
        mensagem = json.loads(linha_bytes.decode("utf-8"))
        salvar_leituras(conexao, mensagem)
        print(f"[{protocolo_esperado}{origem}] Gravado: {mensagem}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Pacote corrompido ou não-JSON: registra e segue em frente
        print(f"[{protocolo_esperado}{origem}] Mensagem inválida (não era JSON): {linha_bytes!r}")
    except ValueError as erro:
        # JSON válido, mas sem os campos mínimos
        print(f"[{protocolo_esperado}{origem}] Mensagem rejeitada ({erro}): {linha_bytes!r}")
    except mariadb.Error as erro:
        # Falha no banco (conexão caiu, tabela errada, etc): registra sem derrubar o listener
        print(f"[{protocolo_esperado}{origem}] Erro ao gravar no banco de dados: {erro}")
        try:
            conexao.close()
        except mariadb.Error:
            pass
        try:
            conexao = conectar_banco()
            print(f"[{protocolo_esperado}{origem}] Reconectando ao banco de dados")
        except mariadb.Error as erro_reconexao:
            print(f"[{protocolo_esperado}{origem}] Reconexão falhou: {erro_reconexao}")
    return conexao


def escutar_udp():
    conexao_db = conectar_banco()
    servidor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    servidor.bind((UDP_HOST, UDP_PORT))
    print(f"[UDP] Escutando em {UDP_HOST}:{UDP_PORT}")

    # UDP não tem conceito de "conexão" cada datagrama é uma mensagem completa e independente
    # então basta receber e processar em loop
    while True:
        dados, endereco = servidor.recvfrom(1024)
        conexao_db = processar_mensagem("UDP", dados, conexao_db, origem=f" {endereco}")


def tratar_cliente_tcp(conn_socket, endereco):
    # Roda em uma thread própria por nó: assim vários nós TCP
    # podem ficar conectados ao mesmo tempo sem um bloquear o outro
    print(f"[TCP] Novo nó conectado: {endereco}")
    buffer = b""
    conexao_db = None
    try:
        # Cada thread tem a sua própria conexão com o banco
        conexao_db = conectar_banco()
        conn_socket.settimeout(TCP_TIMEOUT_SEGUNDOS)
        while True:
            dados = conn_socket.recv(1024)
            if not dados:
                print(f"[TCP] no {endereco} desconectou.")
                break
            # TCP é um fluxo contínuo de bytes, sem limites de mensagem:
            # por isso acumulamos num buffer e só processamos quando
            # encontramos o delimitador \n que marca o fim de uma leitura
            buffer += dados
            while b"\n" in buffer:
                linha, buffer = buffer.split(b"\n", 1)
                if linha.strip():
                    conexao_db = processar_mensagem("TCP", linha, conexao_db, origem=f" {endereco}")
    except socket.timeout:
        print(f"[TCP] no {endereco} ficou {TCP_TIMEOUT_SEGUNDOS}s sem enviar. Encerrando conexão.")
    except mariadb.Error as erro:
        print(f"[TCP] Não foi possível conectar ao banco para o nó {endereco}: {erro}")
    except OSError as erro:
        print(f"[TCP] Erro de rede com o nó {endereco}: {erro}")
    finally:
        conn_socket.close()
        if conexao_db is not None:
            try:
                conexao_db.close()
            except mariadb.Error:
                pass


def escutar_tcp():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permite reiniciar o gateway rapidamente sem esperar a porta ser liberada pelo SO
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((TCP_HOST, TCP_PORT))
    servidor.listen()
    print(f"[TCP] Escutando em {TCP_HOST}:{TCP_PORT}")

    while True:
        conn_socket, endereco = servidor.accept()
        # Uma thread por nó TCP conectado, para atender vários simultaneamente
        threading.Thread(
            target=tratar_cliente_tcp,
            args=(conn_socket, endereco),
            daemon=True,
        ).start()


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