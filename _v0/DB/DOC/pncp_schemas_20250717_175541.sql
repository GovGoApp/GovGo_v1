-- ESQUEMAS SQL GERADOS AUTOMATICAMENTE
-- Data: 2025-07-17 17:55:41
-- Fonte: API PNCP

-- Tabela: pca_pca_consolidado_orgao
CREATE TABLE pca_pca_consolidado_orgao (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    dataAtualizacao TEXT,
    dataPublicacaoPncp TEXT,
    cnpj TEXT(14),
    quantidade INTEGER,
    valorTotal REAL,
    anoPca INTEGER,
    razaoSocial TEXT(21),
    poder TEXT(1),
    esfera TEXT(1)
);

-- Tabela: pca_pca_unidades_orgao
CREATE TABLE pca_pca_unidades_orgao (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    dataPublicacaoPncp TEXT,
    codigoUnidade TEXT(6),
    nomeUnidade TEXT(44),
    valorTotal REAL,
    cnpj TEXT(14),
    anoPca INTEGER,
    razaoSocial TEXT(21),
    dataAtualizacao TEXT,
    dataAtualizacaoGlobalPCA TEXT,
    esfera TEXT(1),
    poder TEXT(1),
    sequencialPca INTEGER,
    quantidade INTEGER,
    numeroControlePNCP TEXT(28)
);

