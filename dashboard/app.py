from flask import Flask, jsonify, request
import mariadb

# Mesmo banco usado pelo gateway.
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "iot",
    "password": "iot123",
    "database": "monitoramento_iot",
}

app = Flask(__name__)

# Quantos pontos, no máximo, cada nó terá em cada gráfico
PONTOS_POR_GRAFICO = 300


def consultar(sql, params=()):
    # Abre uma conexão por requisição (simples e suficiente para um dashboard local)
    conexao = mariadb.connect(**DB_CONFIG)
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, params)
        linhas = cursor.fetchall()
        cursor.close()
        return linhas
    finally:
        conexao.close()


def horas_da_requisicao():
    # Lê ?horas=N da URL, limitando a um intervalo seguro (1 hora a 30 dias)
    try:
        horas = int(request.args.get("horas", 6))
    except ValueError:
        horas = 6
    return max(1, min(horas, 720))


@app.route("/api/resumo")
def api_resumo():
    horas = horas_da_requisicao()

    # Estatísticas por nó dentro do período escolhido
    estatisticas = consultar(
        """
        SELECT no_id, protocolo,
               COUNT(*)            AS total,
               AVG(temperatura)    AS temp_media,
               MIN(temperatura)    AS temp_min,
               MAX(temperatura)    AS temp_max,
               AVG(umidade_ar)     AS ar_media,
               MIN(umidade_ar)     AS ar_min,
               MAX(umidade_ar)     AS ar_max,
               AVG(umidade_solo)   AS solo_media,
               MIN(umidade_solo)   AS solo_min,
               MAX(umidade_solo)   AS solo_max
        FROM leituras
        WHERE recebido_em >= NOW() - INTERVAL ? HOUR
        GROUP BY no_id, protocolo
        """,
        (horas,),
    )

    # Última leitura de cada nó (independente do período), com a idade em segundos
    ultimas = consultar(
        """
        SELECT l.no_id, l.protocolo, l.temperatura, l.umidade_ar, l.umidade_solo,
               l.recebido_em, TIMESTAMPDIFF(SECOND, l.recebido_em, NOW()) AS idade_s
        FROM leituras l
        JOIN (SELECT no_id, MAX(id) AS ultimo_id FROM leituras GROUP BY no_id) m
          ON l.id = m.ultimo_id
        ORDER BY l.no_id
        """
    )
    for linha in ultimas:
        linha["recebido_em"] = linha["recebido_em"].isoformat(sep=" ")

    total_geral = consultar("SELECT COUNT(*) AS total FROM leituras")[0]["total"]

    return jsonify({
        "total_geral": total_geral,
        "estatisticas": estatisticas,
        "ultimas": ultimas,
    })


@app.route("/api/series")
def api_series():
    horas = horas_da_requisicao()

    # Agrupa as leituras em "baldes" de tempo para limitar o número de pontos:
    # com 24h de dados a 10s de intervalo seriam 8.640 pontos por nó
    balde = max(10, (horas * 3600) // PONTOS_POR_GRAFICO)

    # balde é um int calculado aqui (nunca vem direto do usuário), então é seguro no f-string
    linhas = consultar(
        f"""
        SELECT no_id,
               FLOOR(UNIX_TIMESTAMP(recebido_em) / {balde}) * {balde} AS t,
               AVG(temperatura)  AS temperatura,
               AVG(umidade_ar)   AS umidade_ar,
               AVG(umidade_solo) AS umidade_solo
        FROM leituras
        WHERE recebido_em >= NOW() - INTERVAL ? HOUR
        GROUP BY no_id, t
        ORDER BY no_id, t
        """,
        (horas,),
    )

    series = {}
    for linha in linhas:
        no = series.setdefault(linha["no_id"], {"temperatura": [], "umidade_ar": [], "umidade_solo": []})
        x = int(linha["t"]) * 1000  # milissegundos, formato que o JavaScript espera
        for grandeza in ("temperatura", "umidade_ar", "umidade_solo"):
            valor = linha[grandeza]
            no[grandeza].append({"x": x, "y": None if valor is None else round(float(valor), 1)})

    return jsonify(series)
    

if __name__ == "__main__":
    # host 0.0.0.0 permite abrir o dashboard de outro aparelho da rede (ex: celular)
    app.run(host="0.0.0.0", port=8000, debug=False)