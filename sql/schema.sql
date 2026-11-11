-- Cria o banco de dados usado pelo gateway

CREATE DATABASE IF NOT EXISTS monitoramento_iot;
USE monitoramento_iot;

-- Tabela onde cada leitura recebida (via TCP ou UDP) é armazenada

CREATE TABLE IF NOT EXISTS leituras(
    id INT AUTO_INCREMENT PRIMARY KEY,
    no_id VARCHAR(50) NOT NULL,
    protocolo VARCHAR(10) NOT NULL,
    -- momento em que o nó gerou a leitura
    timestamp_no DATETIME NOT NULL,                   
    -- momento em que o gateway recebeu  
    recebido_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,   
    temperatura FLOAT,
    umidade_ar FLOAT,
    umidade_solo FLOAT,

    -- acelera consulta filtrando por nó especifico ou por periodo de tempo
    INDEX idx_no_id(no_id),
    INDEX idx_recebido_em(recebido_em)
);


-- Tabela de alertas: uma linha por episódio de valor abaixo do limite.
-- Enquanto resolvido_em for NULL, o alerta continua ativo.

CREATE TABLE IF NOT EXISTS alertas(
    id INT AUTO_INCREMENT PRIMARY KEY,
    no_id VARCHAR(50) NOT NULL,
    grandeza VARCHAR(20) NOT NULL,
    valor FLOAT NOT NULL,
    limite_minimo FLOAT NOT NULL,
    -- momento em que o valor caiu abaixo do limite
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- momento em que voltou ao normal (NULL = ainda ativo)
    resolvido_em TIMESTAMP NULL DEFAULT NULL,

    -- acelera a busca de "existe alerta ativo para este nó e grandeza?"
    INDEX idx_alertas_ativos(no_id, grandeza, resolvido_em)
);