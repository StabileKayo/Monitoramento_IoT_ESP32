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
