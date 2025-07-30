#!/usr/bin/env python3
"""
GovGo V1 - Setup do Banco de Dados V1
======================================
Cria tabelas baseadas nas estruturas V0 (SQLite + Supabase)
Baseado em PNCP_DB_v2.txt e SUPABASE_v0.txt

ESTRUTURA FASE 1:
1. categorias (Hierarquia de categorias com embeddings)
2. contratacoes (Contratações principais)
3. contratos (Contratos firmados)  
4. itens_contratacao (Itens das contratações)
5. classificacoes_itens (Classificação ML dos itens)
6. contratacoes_embeddings (Embeddings das contratações)
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

console = Console()

class DatabaseSetup:
    """Configurador do banco de dados V1 baseado nas estruturas V0"""
    
    def __init__(self):
        self.connection = None
        
    def connect(self):
        """Conecta ao banco de dados"""
        try:
            self.connection = psycopg2.connect(
                host=os.getenv("SUPABASE_HOST"),
                database=os.getenv("SUPABASE_DBNAME"),
                user=os.getenv("SUPABASE_USER"),
                password=os.getenv("SUPABASE_PASSWORD"),
                port=int(os.getenv("SUPABASE_PORT", "5432"))
            )
            console.print("✅ Conectado ao Supabase com sucesso!")
            return True
        except Exception as e:
            console.print(f"❌ Erro ao conectar: {e}")
            return False
    
    def create_categoria_table(self):
        """1. TABELA CATEGORIA (baseada em PNCP_DB_v2.txt + SUPABASE_v0.txt)"""
        sql = """
        -- Habilitar extensões necessárias
        CREATE EXTENSION IF NOT EXISTS vector;
        
        CREATE TABLE IF NOT EXISTS categoria (
            id BIGSERIAL PRIMARY KEY,
            
            -- Campos originais do PNCP_DB_v2.txt em minúscula
            codcat TEXT UNIQUE NOT NULL,
            nomcat TEXT,
            codnv0 TEXT,
            nomnv0 TEXT,
            codnv1 TEXT,
            nomnv1 TEXT,
            codnv2 TEXT,
            nomnv2 TEXT,
            codnv3 TEXT,
            nomnv3 TEXT,
            
            -- Embeddings (baseado em SUPABASE_v0.txt)
            cat_embeddings vector(1536),
            
            -- Metadados
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Índices para categoria
        CREATE INDEX IF NOT EXISTS idx_categoria_codcat ON categoria(codcat);
        CREATE INDEX IF NOT EXISTS idx_categoria_nomcat ON categoria(nomcat);
        CREATE INDEX IF NOT EXISTS idx_categoria_codnv0 ON categoria(codnv0);
        CREATE INDEX IF NOT EXISTS idx_categoria_codnv1 ON categoria(codnv1);
        
        -- Índice para embeddings usando HNSW
        CREATE INDEX IF NOT EXISTS idx_categoria_embeddings ON categoria 
        USING hnsw (cat_embeddings vector_cosine_ops);
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'categoria' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'categoria': {e}")
            raise
    def create_contratacao_table(self):
        """2. TABELA CONTRATACAO (baseada em PNCP_DB_v2.txt versão 'contratacao')"""
        sql = """
        CREATE TABLE IF NOT EXISTS contratacao (
            id_contratacao BIGSERIAL PRIMARY KEY,
            
            -- Identificação (baseado em PNCP_DB_v2.txt)
            numerocontrolepncp TEXT UNIQUE,
            modadisputaid TEXT,
            amparolegal_codigo TEXT,
            dataaberturaproposta TEXT,
            dataencerramentoproposta TEXT,
            srp TEXT,
            orgaoentidade_cnpj TEXT,
            orgaoentidade_razaosocial TEXT,
            orgaoentidade_poderid TEXT,
            orgaoentidade_esferaid TEXT,
            anocompra TEXT,
            sequencialcompra TEXT,
            processo TEXT,
            objetocompra TEXT,
            valortotalhomologado DECIMAL(15,2),
            datainclusao TEXT,
            datapublicacaopncp TEXT,
            dataatualizacao TEXT,
            numerocompra TEXT,
            unidadeorgao_ufnome TEXT,
            unidadeorgao_ufsigla TEXT,
            unidadeorgao_municipionome TEXT,
            unidadeorgao_codigounidade TEXT,
            unidadeorgao_nomeunidade TEXT,
            unidadeorgao_codigoibge TEXT,
            modalidadeid TEXT,
            dataatualizacaoglobal TEXT,
            tipoinstrumentoconvocatoriocodigo TEXT,
            valortotalestimado TEXT,
            situacaocompraid TEXT,
            codcat TEXT,
            score DECIMAL(6,4),
            informacaocomplementar TEXT,
            justificativapresencial TEXT,
            linksistemaorigem TEXT,
            linkprocessoeletronico TEXT,
            amparolegal_nome TEXT,
            amparolegal_descricao TEXT,
            modalidadenome TEXT,
            modadisputanome TEXT,
            tipoinstrumentoconvocatorionome TEXT,
            situacaocompranome TEXT,
            existeresultado BOOLEAN,
            orcamentosigilosocodigo INTEGER,
            orcamentosigioso_descricao TEXT,
            orgaosurogado_cnpj TEXT,
            orgaosurogado_razaosocial TEXT,
            orgaosurogado_poderid TEXT,
            orgaosurogado_esferaid TEXT,
            unidadesurogada_ufnome TEXT,
            unidadesurogada_ufsigla TEXT,
            unidadesurogada_municipionome TEXT,
            unidadesurogada_codigounidade TEXT,
            unidadesurogada_nomeunidade TEXT,
            unidadesurogada_codigoibge TEXT,
            usuarionome TEXT,
            fontesorcamentarias TEXT,
            
            -- Metadados
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            
            -- Chave estrangeira
            FOREIGN KEY (codcat) REFERENCES categoria(codcat)
        );
        
        -- Índices para contratacao
        CREATE INDEX IF NOT EXISTS idx_contratacao_numerocontrolepncp ON contratacao(numerocontrolepncp);
        CREATE INDEX IF NOT EXISTS idx_contratacao_anocompra ON contratacao(anocompra);
        CREATE INDEX IF NOT EXISTS idx_contratacao_municipio ON contratacao(unidadeorgao_municipionome);
        CREATE INDEX IF NOT EXISTS idx_contratacao_uf ON contratacao(unidadeorgao_ufsigla);
        CREATE INDEX IF NOT EXISTS idx_contratacao_modalidade ON contratacao(modalidadeid);
        CREATE INDEX IF NOT EXISTS idx_contratacao_valor ON contratacao(valortotalestimado);
        CREATE INDEX IF NOT EXISTS idx_contratacao_codcat ON contratacao(codcat);
        
        -- Índice para busca de texto
        CREATE INDEX IF NOT EXISTS idx_contratacao_objeto_gin ON contratacao 
        USING gin(to_tsvector('portuguese', objetocompra));
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'contratacao' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'contratacao': {e}")
            raise
    
    def create_contrato_table(self):
        """3. TABELA CONTRATO (baseada em PNCP_DB_v2.txt)"""
        sql = """
        CREATE TABLE IF NOT EXISTS contrato (
            id_contrato BIGSERIAL PRIMARY KEY,
            
            -- Identificação (baseado em PNCP_DB_v2.txt)
            numerocontrolepncpcompra TEXT NOT NULL,
            numerocontrolepncp TEXT,
            numerocontratoempenho TEXT,
            anocontrato TEXT,
            dataassinatura TEXT,
            datavigenciainicio TEXT,
            datavigenciafim TEXT,
            nifornecedor TEXT,
            tipopessoa TEXT,
            sequencialcontrato TEXT,
            processo TEXT,
            nomerazaosocialfornecedor TEXT,
            numeroparcelas TEXT,
            numeroretificacao TEXT,
            objetocontrato TEXT,
            valorinicial DECIMAL(15,2),
            valorparcela DECIMAL(15,2),
            valorglobal DECIMAL(15,2),
            dataatualizacaoglobal TEXT,
            tipocontrato_id TEXT,
            tipocontrato_nome TEXT,
            orgaoentidade_cnpj TEXT,
            orgaoentidade_razaosocial TEXT,
            orgaoentidade_poderid TEXT,
            orgaoentidade_esferaid TEXT,
            categoriaprocesso_id TEXT,
            categoriaprocesso_nome TEXT,
            unidadeorgao_ufnome TEXT,
            unidadeorgao_codigounidade TEXT,
            unidadeorgao_nomeunidade TEXT,
            unidadeorgao_ufsigla TEXT,
            unidadeorgao_municipionome TEXT,
            unidadeorgao_codigoibge TEXT,
            vigenciaano TEXT,
            
            -- Metadados
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            
            -- Constraints
            UNIQUE(numerocontrolepncpcompra),
            FOREIGN KEY (numerocontrolepncpcompra) REFERENCES contratacao(numerocontrolepncp)
        );
        
        -- Índices para contrato
        CREATE INDEX IF NOT EXISTS idx_contrato_numerocontrolepncpcompra ON contrato(numerocontrolepncpcompra);
        CREATE INDEX IF NOT EXISTS idx_contrato_numerocontrolepncp ON contrato(numerocontrolepncp);
        CREATE INDEX IF NOT EXISTS idx_contrato_anocontrato ON contrato(anocontrato);
        CREATE INDEX IF NOT EXISTS idx_contrato_nifornecedor ON contrato(nifornecedor);
        CREATE INDEX IF NOT EXISTS idx_contrato_valorglobal ON contrato(valorglobal);
        
        -- Índice para busca de texto
        CREATE INDEX IF NOT EXISTS idx_contrato_objeto_gin ON contrato 
        USING gin(to_tsvector('portuguese', objetocontrato));
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'contrato' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'contrato': {e}")
            raise
    
    def create_item_contratacao_table(self):
        """4. TABELA ITEM_CONTRATACAO (baseada em PNCP_DB_v2.txt)"""
        sql = """
        CREATE TABLE IF NOT EXISTS item_contratacao (
            id_item_contratacao BIGSERIAL PRIMARY KEY,
            
            -- Identificação (baseado em PNCP_DB_v2.txt)
            numerocontrolepncp TEXT NOT NULL,
            numeroitem TEXT NOT NULL,
            
            -- Descrição e tipo
            descricao TEXT,
            materialouservico TEXT,
            
            -- Valores financeiros
            valorunitarioestimado DECIMAL(15,2),
            valortotal DECIMAL(15,2),
            quantidade DECIMAL(15,3),
            unidademedida TEXT,
            
            -- Categoria do item
            itemcategoriaid TEXT,
            itemcategorianome TEXT,
            
            -- Critério de julgamento
            criteriojulgamentoid TEXT,
            
            -- Situação do item
            situacaocompraitem TEXT,
            
            -- Benefícios
            tipobeneficio TEXT,
            
            -- Datas
            datainclusao TEXT,
            dataatualizacao TEXT,
            
            -- NCM/NBS
            ncmnbscodigo TEXT,
            
            -- Catálogo
            catalogo TEXT,
            
            -- Metadados
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            
            -- Constraints
            UNIQUE(numerocontrolepncp, numeroitem),
            FOREIGN KEY (numerocontrolepncp) REFERENCES contratacao(numerocontrolepncp)
        );
        
        -- Índices para item_contratacao
        CREATE INDEX IF NOT EXISTS idx_item_contratacao_numerocontrolepncp ON item_contratacao(numerocontrolepncp);
        CREATE INDEX IF NOT EXISTS idx_item_contratacao_numeroitem ON item_contratacao(numeroitem);
        CREATE INDEX IF NOT EXISTS idx_item_contratacao_itemcategoriaid ON item_contratacao(itemcategoriaid);
        CREATE INDEX IF NOT EXISTS idx_item_contratacao_valortotal ON item_contratacao(valortotal);
        CREATE INDEX IF NOT EXISTS idx_item_contratacao_materialouservico ON item_contratacao(materialouservico);
        
        -- Índice para busca de texto
        CREATE INDEX IF NOT EXISTS idx_item_contratacao_descricao_gin ON item_contratacao 
        USING gin(to_tsvector('portuguese', descricao));
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'item_contratacao' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'item_contratacao': {e}")
            raise
    
    def create_item_classificacao_table(self):
        """5. TABELA ITEM_CLASSIFICACAO (baseada em PNCP_DB_v2.txt)"""
        sql = """
        CREATE TABLE IF NOT EXISTS item_classificacao (
            id_item_classificacao BIGSERIAL PRIMARY KEY,
            
            -- Relacionamento com item_contratacao
            id_item_contratacao BIGINT NOT NULL,
            numerocontrolepncp TEXT NOT NULL,
            numeroitem TEXT NOT NULL,
            
            -- Dados da classificação
            codigoclasse TEXT,
            nomeclasse TEXT,
            codigopdp TEXT,
            descricaopdp TEXT,
            
            -- Tipo de classificação
            tipoclassificacao TEXT,
            nivelclassificacao TEXT,
            
            -- Metadados
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            
            -- Constraints
            FOREIGN KEY (id_item_contratacao) REFERENCES item_contratacao(id_item_contratacao),
            FOREIGN KEY (numerocontrolepncp) REFERENCES contratacao(numerocontrolepncp)
        );
        
        -- Índices para item_classificacao
        CREATE INDEX IF NOT EXISTS idx_item_classificacao_item_id ON item_classificacao(id_item_contratacao);
        CREATE INDEX IF NOT EXISTS idx_item_classificacao_numerocontrolepncp ON item_classificacao(numerocontrolepncp);
        CREATE INDEX IF NOT EXISTS idx_item_classificacao_numeroitem ON item_classificacao(numeroitem);
        CREATE INDEX IF NOT EXISTS idx_item_classificacao_codigoclasse ON item_classificacao(codigoclasse);
        CREATE INDEX IF NOT EXISTS idx_item_classificacao_codigopdp ON item_classificacao(codigopdp);
        
        -- Índice para busca de texto
        CREATE INDEX IF NOT EXISTS idx_item_classificacao_nomeclasse_gin ON item_classificacao 
        USING gin(to_tsvector('portuguese', nomeclasse));
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'item_classificacao' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'item_classificacao': {e}")
            raise
    
    def create_contratacao_emb_table(self):
        """6. TABELA CONTRATACAO_EMB (baseada em SUPABASE_v0.txt)"""
        sql = """
        CREATE TABLE IF NOT EXISTS contratacao_emb (
            id BIGSERIAL PRIMARY KEY,
            
            -- Identificação (baseado em SUPABASE_v0.txt)
            numerocontrolepncp TEXT NOT NULL,
            
            -- Embedding vector
            embedding_vector vector(1536),
            
            -- Metadados do modelo
            modelo_embedding TEXT DEFAULT 'text-embedding-3-large',
            metadata JSONB,
            confidence DECIMAL(6,4),
            
            -- Categorias e similaridades (arrays)
            top_categories TEXT[],
            top_similarities DECIMAL(6,4)[],
            
            -- Timestamps
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            
            -- Constraints
            FOREIGN KEY (numerocontrolepncp) REFERENCES contratacao(numerocontrolepncp)
        );
        
        -- Índices para contratacao_emb
        CREATE INDEX IF NOT EXISTS idx_contratacao_emb_numerocontrolepncp ON contratacao_emb(numerocontrolepncp);
        CREATE INDEX IF NOT EXISTS idx_contratacao_emb_confidence ON contratacao_emb(confidence);
        CREATE INDEX IF NOT EXISTS idx_contratacao_emb_modelo ON contratacao_emb(modelo_embedding);
        
        -- Índice para embeddings usando HNSW
        CREATE INDEX IF NOT EXISTS idx_contratacao_emb_vector ON contratacao_emb 
        USING hnsw (embedding_vector vector_cosine_ops);
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'contratacao_emb' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'contratacao_emb': {e}")
            raise
    
    def create_contrato_emb_table(self):
        """7. TABELA CONTRATO_EMB (na mesma formatação de contratacao_emb)"""
        sql = """
        CREATE TABLE IF NOT EXISTS contrato_emb (
            id BIGSERIAL PRIMARY KEY,
            
            -- Identificação (baseado em contratacao_emb)
            numerocontrolepncpcompra TEXT NOT NULL,
            
            -- Embedding vector
            embedding_vector vector(1536),
            
            -- Metadados do modelo
            modelo_embedding TEXT DEFAULT 'text-embedding-3-large',
            metadata JSONB,
            confidence DECIMAL(6,4),
            
            -- Categorias e similaridades (arrays)
            top_categories TEXT[],
            top_similarities DECIMAL(6,4)[],
            
            -- Timestamps
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            
            -- Constraints
            FOREIGN KEY (numerocontrolepncpcompra) REFERENCES contrato(numerocontrolepncpcompra)
        );
        
        -- Índices para contrato_emb
        CREATE INDEX IF NOT EXISTS idx_contrato_emb_numerocontrolepncpcompra ON contrato_emb(numerocontrolepncpcompra);
        CREATE INDEX IF NOT EXISTS idx_contrato_emb_confidence ON contrato_emb(confidence);
        CREATE INDEX IF NOT EXISTS idx_contrato_emb_modelo ON contrato_emb(modelo_embedding);
        
        -- Índice para embeddings usando HNSW
        CREATE INDEX IF NOT EXISTS idx_contrato_emb_vector ON contrato_emb 
        USING hnsw (embedding_vector vector_cosine_ops);
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'contrato_emb' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'contrato_emb': {e}")
            raise
    
    def create_ata_preco_table(self):
        """8. TABELA ATA_PRECO (baseada na API PNCP - Atas de Registro de Preços)"""
        sql = """
        CREATE TABLE IF NOT EXISTS ata_preco (
            id_ata_preco BIGSERIAL PRIMARY KEY,
            
            -- Identificação (baseado no Manual PNCP v2.2.1)
            numerocontrolepncpcompra TEXT NOT NULL,
            numeroataregistropreco TEXT NOT NULL,
            anoata INTEGER,
            sequencialta INTEGER,
            
            -- Datas
            dataassinatura TEXT,
            datavigenciainicio TEXT,
            datavigenciafim TEXT,
            datacancelamento TEXT,
            datapublicacaopncp TEXT,
            datainclusao TEXT,
            dataatualizacao TEXT,
            
            -- Status
            cancelado BOOLEAN DEFAULT FALSE,
            
            -- Objeto e valores
            objetoata TEXT,
            valorestimadototal DECIMAL(15,2),
            
            -- Órgão gerenciador
            orgaogerenciadorcnpj TEXT,
            orgaogerenciadornome TEXT,
            
            -- Fornecedores (JSON para múltiplos fornecedores)
            fornecedores JSONB,
            
            -- Metadados
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            
            -- Chave estrangeira
            FOREIGN KEY (numerocontrolepncpcompra) REFERENCES contratacao(numerocontrolepncp)
        );
        
        -- Índices para ata_preco
        CREATE INDEX IF NOT EXISTS idx_ata_preco_numerocontrolepncpcompra ON ata_preco(numerocontrolepncpcompra);
        CREATE INDEX IF NOT EXISTS idx_ata_preco_numeroataregistropreco ON ata_preco(numeroataregistropreco);
        CREATE INDEX IF NOT EXISTS idx_ata_preco_anoata ON ata_preco(anoata);
        CREATE INDEX IF NOT EXISTS idx_ata_preco_orgaogerenciadorcnpj ON ata_preco(orgaogerenciadorcnpj);
        CREATE INDEX IF NOT EXISTS idx_ata_preco_cancelado ON ata_preco(cancelado);
        
        -- Índice para busca de texto no objeto da ata
        CREATE INDEX IF NOT EXISTS idx_ata_preco_objeto_gin ON ata_preco 
        USING gin(to_tsvector('portuguese', objetoata));
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'ata_preco' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'ata_preco': {e}")
            raise
    
    def create_pca_table(self):
        """9. TABELA PCA (baseada na API PNCP - Plano de Contratações Anuais)"""
        sql = """
        CREATE TABLE IF NOT EXISTS pca (
            id_pca BIGSERIAL PRIMARY KEY,
            
            -- Identificação do órgão (baseado no Manual PNCP v2.2.1)
            cnpj TEXT NOT NULL,
            razaosocial TEXT,
            codigounidade TEXT,
            nomeunidade TEXT,
            
            -- Ano do PCA
            anopca INTEGER NOT NULL,
            
            -- Valores
            valortotal DECIMAL(15,2),
            quantidade INTEGER,
            
            -- Localização
            municipionome TEXT,
            municipiocodigoibge TEXT,
            ufsigla TEXT,
            ufnome TEXT,
            
            -- Poder e esfera
            poder TEXT,
            esfera TEXT,
            
            -- Sequencial do PCA
            sequencialpca INTEGER,
            
            -- Datas
            datapublicacaopncp TEXT,
            datainclusao TEXT,
            dataatualizacao TEXT,
            dataatualizacaoglobalpca TEXT,
            
            -- Itens do plano (JSON para flexibilidade)
            itensplano JSONB,
            
            -- Controle PNCP
            numerocontrolepncp TEXT,
            
            -- Metadados
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            
            -- Constraints
            UNIQUE(cnpj, codigounidade, anopca)
        );
        
        -- Índices para pca
        CREATE INDEX IF NOT EXISTS idx_pca_cnpj ON pca(cnpj);
        CREATE INDEX IF NOT EXISTS idx_pca_anopca ON pca(anopca);
        CREATE INDEX IF NOT EXISTS idx_pca_codigounidade ON pca(codigounidade);
        CREATE INDEX IF NOT EXISTS idx_pca_valortotal ON pca(valortotal);
        CREATE INDEX IF NOT EXISTS idx_pca_poder ON pca(poder);
        CREATE INDEX IF NOT EXISTS idx_pca_esfera ON pca(esfera);
        CREATE INDEX IF NOT EXISTS idx_pca_ufsigla ON pca(ufsigla);
        
        -- Índice para busca de texto
        CREATE INDEX IF NOT EXISTS idx_pca_razaosocial_gin ON pca 
        USING gin(to_tsvector('portuguese', razaosocial));
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'pca' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'pca': {e}")
            raise
    
    def create_categorias_table(self):
        """1. TABELA CATEGORIAS (baseada em PNCP_DB_v2 + embeddings do SUPABASE_v0)"""
        sql = """
        CREATE TABLE IF NOT EXISTS categorias (
            id BIGSERIAL PRIMARY KEY,
            
            -- Identificação (baseado em PNCP_DB_v2.txt)
            codigo VARCHAR(20) UNIQUE NOT NULL,
            descricao TEXT NOT NULL,
            nivel INTEGER NOT NULL DEFAULT 1,
            categoria_pai_codigo VARCHAR(20),
            hierarquia_completa TEXT,
            ativo BOOLEAN DEFAULT true,
            
            -- Embedding (baseado em SUPABASE_v0.txt)
            embedding vector(1536), -- Para OpenAI embeddings
            
            -- Metadados
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            
            -- Foreign Key para hierarquia
            FOREIGN KEY (categoria_pai_codigo) REFERENCES categorias(codigo) ON DELETE SET NULL
        );
        
        -- Índices para categorias
        CREATE INDEX IF NOT EXISTS idx_categorias_codigo ON categorias(codigo);
        CREATE INDEX IF NOT EXISTS idx_categorias_nivel ON categorias(nivel);
        CREATE INDEX IF NOT EXISTS idx_categorias_pai ON categorias(categoria_pai_codigo);
        CREATE INDEX IF NOT EXISTS idx_categorias_ativo ON categorias(ativo);
        CREATE INDEX IF NOT EXISTS idx_categorias_embedding ON categorias USING hnsw (embedding vector_cosine_ops);
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'categorias' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'categorias': {e}")
            raise
    
    def create_additional_indexes_and_constraints(self):
        """Criar índices adicionais e constraints para performance"""
        sql = """
        -- Índices compostos para queries comuns
        CREATE INDEX IF NOT EXISTS idx_contratacao_ano_uf ON contratacao(anocompra, unidadeorgao_ufsigla);
        CREATE INDEX IF NOT EXISTS idx_contrato_ano_valor ON contrato(anocontrato, valorglobal);
        CREATE INDEX IF NOT EXISTS idx_item_categoria_valor ON item_contratacao(itemcategoriaid, valortotal);
        
        -- Função de atualização automática de updated_at
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        -- Triggers para atualização automática
        CREATE TRIGGER update_contratacao_updated_at BEFORE UPDATE ON contratacao 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        CREATE TRIGGER update_contrato_updated_at BEFORE UPDATE ON contrato 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        CREATE TRIGGER update_item_contratacao_updated_at BEFORE UPDATE ON item_contratacao 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        CREATE TRIGGER update_item_classificacao_updated_at BEFORE UPDATE ON item_classificacao 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        CREATE TRIGGER update_ata_preco_updated_at BEFORE UPDATE ON ata_preco 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        CREATE TRIGGER update_pca_updated_at BEFORE UPDATE ON pca 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Índices adicionais e triggers criados com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar índices adicionais: {e}")
            raise
    
    def setup_database(self):
        """Executa o setup completo do banco de dados"""
        console.print(Panel.fit(
            "[bold blue]GovGo V1 - Setup Banco de Dados[/bold blue]\n"
            "Criando 9 tabelas baseadas em V0 (SQLite + Supabase) + API Manual:\n"
            "1. categoria (Hierarquia com embeddings)\n"
            "2. contratacao (Contratações principais)\n"
            "3. contrato (Contratos firmados)\n"
            "4. item_contratacao (Itens das contratações)\n"
            "5. item_classificacao (Classificação dos itens)\n"
            "6. contratacao_emb (Embeddings das contratações)\n"
            "7. contrato_emb (Embeddings dos contratos)\n"
            "8. ata_preco (Atas de Registro de Preços)\n"
            "9. pca (Plano de Contratações Anuais)",
            title="🚀 Setup Database V1"
        ))
        
        if not self.connect():
            return False
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                
                task = progress.add_task("Criando tabelas...", total=10)
                
                progress.update(task, description="Criando tabela categoria...")
                self.create_categoria_table()
                progress.advance(task)
                
                progress.update(task, description="Criando tabela contratacao...")
                self.create_contratacao_table()
                progress.advance(task)
                
                progress.update(task, description="Criando tabela contrato...")
                self.create_contrato_table()
                progress.advance(task)
                
                progress.update(task, description="Criando tabela item_contratacao...")
                self.create_item_contratacao_table()
                progress.advance(task)
                
                progress.update(task, description="Criando tabela item_classificacao...")
                self.create_item_classificacao_table()
                progress.advance(task)
                
                progress.update(task, description="Criando tabela contratacao_emb...")
                self.create_contratacao_emb_table()
                progress.advance(task)
                
                progress.update(task, description="Criando tabela contrato_emb...")
                self.create_contrato_emb_table()
                progress.advance(task)
                
                progress.update(task, description="Criando tabela ata_preco...")
                self.create_ata_preco_table()
                progress.advance(task)
                
                progress.update(task, description="Criando tabela pca...")
                self.create_pca_table()
                progress.advance(task)
                
                progress.update(task, description="Criando índices e triggers...")
                self.create_additional_indexes_and_constraints()
                progress.advance(task)
            
            console.print("\n🎉 [bold green]Setup do banco de dados V1 concluído com sucesso![/bold green]")
            
            # Exibir resumo das tabelas criadas
            table = Table(title="📊 Tabelas V1 Criadas")
            table.add_column("Tabela", style="cyan", no_wrap=True)
            table.add_column("Origem", style="magenta")
            table.add_column("Descrição", style="green")
            
            table.add_row("categoria", "PNCP_DB_v2 + SUPABASE_v0", "Hierarquia de categorias com embeddings")
            table.add_row("contratacao", "PNCP_DB_v2", "Contratações principais do PNCP")
            table.add_row("contrato", "PNCP_DB_v2", "Contratos firmados")
            table.add_row("item_contratacao", "PNCP_DB_v2", "Itens das contratações")
            table.add_row("item_classificacao", "PNCP_DB_v2", "Classificação dos itens")
            table.add_row("contratacao_emb", "SUPABASE_v0", "Embeddings das contratações")
            table.add_row("contrato_emb", "SUPABASE_v0", "Embeddings dos contratos")
            table.add_row("ata_preco", "API Manual PNCP", "Atas de Registro de Preços")
            table.add_row("pca", "API Manual PNCP", "Plano de Contratações Anuais")
            
            console.print(table)
            
            return True
            
        except Exception as e:
            console.print(f"\n❌ [bold red]Erro durante o setup: {e}[/bold red]")
            return False
        
        finally:
            if self.connection:
                self.connection.close()
                console.print("🔌 Conexão com banco de dados fechada")

def main():
    """Função principal"""
    setup = DatabaseSetup()
    
    if setup.setup_database():
        console.print("\n✅ [bold green]Database setup concluído com sucesso![/bold green]")
        console.print("🚀 Agora você pode prosseguir com a migração dos dados do V0 para o Supabase")
    else:
        console.print("\n❌ [bold red]Falha no setup do database[/bold red]")
        exit(1)

if __name__ == "__main__":
    main()
