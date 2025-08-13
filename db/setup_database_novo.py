#!/usr/bin/env python3
"""
GovGo V1 - Setup do Banco de Dados COMPLETO
============================================
Cria e configura TODAS as 7 tabelas específicas no Supabase
Baseado na estrutura SQLite V0 + Manual PNCP

ESTRUTURA:
1. contratacoes (Compras/Editais/Avisos) 
2. contratos (Contratos firmados)
3. itens_contratacao (Itens das contratações)
4. classificacoes_itens (Classificação ML dos itens)
5. categorias (Categorias de produtos)
6. atas (NOVO - Atas de Registro de Preço)
7. pcas (NOVO - Planos de Contratações)
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from core.config import config
from core.utils import configurar_logging

console = Console()
configurar_logging()

class DatabaseSetup:
    """Configurador do banco de dados com 7 tabelas específicas"""
    
    def __init__(self):
        self.connection = None
        
    def connect(self):
        """Conecta ao banco de dados"""
        try:
            self.connection = psycopg2.connect(
                host=config.supabase_host,
                database=config.supabase_database,
                user=config.supabase_user,
                password=config.supabase_password,
                port=config.supabase_port
            )
            console.print("✅ Conectado ao Supabase com sucesso!")
            return True
        except Exception as e:
            console.print(f"❌ Erro ao conectar: {e}")
            return False
    
    def create_contratacoes_table(self):
        """1. TABELA CONTRATACOES (Compras/Editais/Avisos)"""
        sql = """
        CREATE TABLE IF NOT EXISTS contratacoes (
            id BIGSERIAL PRIMARY KEY,
            
            -- Identificação
            numero_controle_pncp TEXT UNIQUE NOT NULL,
            ano_compra INTEGER,
            sequencial_compra INTEGER,
            numero_compra TEXT,
            processo TEXT,
            
            -- Valores
            valor_total_estimado DECIMAL(15,2),
            valor_total_homologado DECIMAL(15,2),
            orcamento_sigiloso_codigo TEXT,
            orcamento_sigiloso_descricao TEXT,
            
            -- Modalidade e disputa
            modalidade_id INTEGER,
            modalidade_nome TEXT,
            modo_disputa_id INTEGER,
            modo_disputa_nome TEXT,
            tipo_instrumento_convocatorio_codigo TEXT,
            tipo_instrumento_convocatorio_nome TEXT,
            
            -- Amparo legal
            amparo_legal_codigo TEXT,
            amparo_legal_nome TEXT,
            amparo_legal_descricao TEXT,
            
            -- Objeto e informações
            objeto_compra TEXT,
            informacao_complementar TEXT,
            justificativa_presencial TEXT,
            srp INTEGER,
            
            -- Links
            link_sistema_origem TEXT,
            link_processo_eletronico TEXT,
            
            -- Situação
            situacao_compra_id INTEGER,
            situacao_compra_nome TEXT,
            existe_resultado INTEGER,
            
            -- Datas
            data_publicacao_pncp TIMESTAMPTZ,
            data_abertura_proposta TIMESTAMPTZ,
            data_encerramento_proposta TIMESTAMPTZ,
            data_inclusao TIMESTAMPTZ,
            data_atualizacao TIMESTAMPTZ,
            data_atualizacao_global TIMESTAMPTZ,
            
            -- Órgão e entidade
            orgao_entidade_razao_social TEXT,
            orgao_entidade_nome_fantasia TEXT,
            orgao_entidade_cnpj TEXT,
            orgao_entidade_municipio_nome TEXT,
            orgao_entidade_municipio_ibge TEXT,
            orgao_entidade_municipio_uf_sigla TEXT,
            orgao_entidade_municipio_uf_nome TEXT,
            orgao_entidade_poder_codigo INTEGER,
            orgao_entidade_poder_nome TEXT,
            orgao_entidade_esfera_id INTEGER,
            orgao_entidade_esfera TEXT,
            orgao_entidade_tipo_organizacao TEXT,
            
            -- Endereço do órgão
            orgao_entidade_endereco_logradouro TEXT,
            orgao_entidade_endereco_numero TEXT,
            orgao_entidade_endereco_bairro TEXT,
            orgao_entidade_endereco_cep TEXT,
            orgao_entidade_endereco_complemento TEXT,
            orgao_entidade_endereco_ddd TEXT,
            orgao_entidade_endereco_telefone TEXT,
            orgao_entidade_endereco_email TEXT,
            orgao_entidade_endereco_site TEXT,
            
            -- Unidade órgão
            unidade_orgao_nome TEXT,
            unidade_orgao_codigo_unidade TEXT,
            unidade_orgao_nome_unidade TEXT,
            unidade_orgao_municipio_nome TEXT,
            unidade_orgao_municipio_ibge TEXT,
            unidade_orgao_municipio_uf_sigla TEXT,
            unidade_orgao_municipio_uf_nome TEXT,
            
            -- Usuário
            usuario_nome TEXT,
            usuario_id INTEGER,
            
            -- Outros campos específicos
            tipo_recurso TEXT,
            is_srp INTEGER,
            is_orcamento_sigiloso INTEGER,
            existe_contrato_associado INTEGER,
            
            -- Órgão sub-rogado
            orgao_sub_rogado_cnpj TEXT,
            orgao_sub_rogado_razao_social TEXT,
            orgao_sub_rogado_poder_id TEXT,
            orgao_sub_rogado_esfera_id TEXT,
            unidade_sub_rogada_uf_nome TEXT,
            unidade_sub_rogada_uf_sigla TEXT,
            unidade_sub_rogada_municipio_nome TEXT,
            unidade_sub_rogada_codigo_unidade TEXT,
            unidade_sub_rogada_nome_unidade TEXT,
            unidade_sub_rogada_codigo_ibge TEXT,
            
            -- Classificação e categorização
            codigo_categoria TEXT,
            score_categoria DECIMAL(5,4),
            fontes_orcamentarias TEXT,
            
            -- Observações
            observacoes TEXT,
            descricao_completa TEXT,
            
            -- Metadados
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Índices para contratacoes
        CREATE INDEX IF NOT EXISTS idx_contratacoes_numero_controle ON contratacoes(numero_controle_pncp);
        CREATE INDEX IF NOT EXISTS idx_contratacoes_ano_compra ON contratacoes(ano_compra);
        CREATE INDEX IF NOT EXISTS idx_contratacoes_municipio ON contratacoes(unidade_orgao_municipio_nome);
        CREATE INDEX IF NOT EXISTS idx_contratacoes_uf ON contratacoes(unidade_orgao_municipio_uf_sigla);
        CREATE INDEX IF NOT EXISTS idx_contratacoes_modalidade ON contratacoes(modalidade_id);
        CREATE INDEX IF NOT EXISTS idx_contratacoes_valor ON contratacoes(valor_total_estimado);
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'contratacoes' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'contratacoes': {e}")
            raise
    
    def create_contratos_table(self):
        """2. TABELA CONTRATOS (Contratos firmados)"""
        sql = """
        CREATE TABLE IF NOT EXISTS contratos (
            id BIGSERIAL PRIMARY KEY,
            
            -- Identificação
            numero_controle_pncp_compra TEXT NOT NULL,
            numero_controle_pncp TEXT,
            numero_contrato_empenho TEXT,
            ano_contrato TEXT,
            sequencial_contrato TEXT,
            processo TEXT,
            
            -- Datas do contrato
            data_assinatura TIMESTAMPTZ,
            data_vigencia_inicio TIMESTAMPTZ,
            data_vigencia_fim TIMESTAMPTZ,
            data_atualizacao_global TIMESTAMPTZ,
            
            -- Fornecedor
            ni_fornecedor TEXT,
            tipo_pessoa TEXT,
            nome_razao_social_fornecedor TEXT,
            tipo_pessoa_subcontratada TEXT,
            
            -- Valores financeiros
            numero_parcelas TEXT,
            numero_retificacao TEXT,
            valor_inicial DECIMAL(15,2),
            valor_parcela DECIMAL(15,2),
            valor_global DECIMAL(15,2),
            valor_acumulado DECIMAL(15,2),
            receita DECIMAL(15,2),
            
            -- Objeto e descrição
            objeto_contrato TEXT,
            informacao_complementar TEXT,
            
            -- Tipo de contrato
            tipo_contrato_id TEXT,
            tipo_contrato_nome TEXT,
            
            -- Órgão e entidade
            orgao_entidade_cnpj TEXT,
            orgao_entidade_razao_social TEXT,
            orgao_entidade_poder_id TEXT,
            orgao_entidade_esfera_id TEXT,
            
            -- Categoria do processo
            categoria_processo_id TEXT,
            categoria_processo_nome TEXT,
            
            -- Unidade do órgão
            unidade_orgao_uf_nome TEXT,
            unidade_orgao_codigo_unidade TEXT,
            unidade_orgao_nome_unidade TEXT,
            unidade_orgao_uf_sigla TEXT,
            unidade_orgao_municipio_nome TEXT,
            unidade_orgao_codigo_ibge TEXT,
            
            -- Outros campos
            vigencia_ano TEXT,
            identificador_cipi TEXT,
            url_cipi TEXT,
            usuario_nome TEXT,
            
            -- Metadados
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            
            -- Chave estrangeira
            FOREIGN KEY (numero_controle_pncp_compra) REFERENCES contratacoes(numero_controle_pncp)
        );
        
        -- Índices para contratos
        CREATE INDEX IF NOT EXISTS idx_contratos_numero_controle_compra ON contratos(numero_controle_pncp_compra);
        CREATE INDEX IF NOT EXISTS idx_contratos_numero_controle ON contratos(numero_controle_pncp);
        CREATE INDEX IF NOT EXISTS idx_contratos_ano ON contratos(ano_contrato);
        CREATE INDEX IF NOT EXISTS idx_contratos_fornecedor ON contratos(ni_fornecedor);
        CREATE INDEX IF NOT EXISTS idx_contratos_valor ON contratos(valor_global);
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'contratos' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'contratos': {e}")
            raise
    
    def create_itens_contratacao_table(self):
        """3. TABELA ITENS_CONTRATACAO (Itens das contratações)"""
        sql = """
        CREATE TABLE IF NOT EXISTS itens_contratacao (
            id BIGSERIAL PRIMARY KEY,
            
            -- Identificação
            numero_controle_pncp TEXT NOT NULL,
            numero_item TEXT NOT NULL,
            
            -- Descrição e tipo
            descricao TEXT,
            material_ou_servico TEXT,
            material_ou_servico_nome TEXT,
            
            -- Valores financeiros
            valor_unitario_estimado DECIMAL(15,2),
            valor_total DECIMAL(15,2),
            quantidade DECIMAL(15,3),
            unidade_medida TEXT,
            
            -- Orçamento
            orcamento_sigiloso TEXT,
            
            -- Categoria do item
            item_categoria_id TEXT,
            item_categoria_nome TEXT,
            
            -- Patrimônio e registro
            patrimonio TEXT,
            codigo_registro_imobiliario TEXT,
            
            -- Critério de julgamento
            criterio_julgamento_id TEXT,
            criterio_julgamento_nome TEXT,
            
            -- Situação do item
            situacao_compra_item TEXT,
            situacao_compra_item_nome TEXT,
            
            -- Benefícios
            tipo_beneficio TEXT,
            tipo_beneficio_nome TEXT,
            incentivo_produtivo_basico TEXT,
            
            -- Datas
            data_inclusao TIMESTAMPTZ,
            data_atualizacao TIMESTAMPTZ,
            
            -- Resultado
            tem_resultado TEXT,
            
            -- Imagem
            imagem TEXT,
            
            -- Margem de preferência
            aplicabilidade_margem_preferencia_normal TEXT,
            aplicabilidade_margem_preferencia_adicional TEXT,
            percentual_margem_preferencia_normal DECIMAL(5,2),
            percentual_margem_preferencia_adicional DECIMAL(5,2),
            
            -- NCM/NBS
            ncm_nbs_codigo TEXT,
            ncm_nbs_descricao TEXT,
            
            -- Catálogo
            catalogo TEXT,
            categoria_item_catalogo TEXT,
            catalogo_codigo_item TEXT,
            
            -- Informações complementares
            informacao_complementar TEXT,
            
            -- Metadados
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            
            -- Constraints
            UNIQUE(numero_controle_pncp, numero_item),
            FOREIGN KEY (numero_controle_pncp) REFERENCES contratacoes(numero_controle_pncp)
        );
        
        -- Índices para itens_contratacao
        CREATE INDEX IF NOT EXISTS idx_itens_numero_controle ON itens_contratacao(numero_controle_pncp);
        CREATE INDEX IF NOT EXISTS idx_itens_numero_item ON itens_contratacao(numero_item);
        CREATE INDEX IF NOT EXISTS idx_itens_categoria ON itens_contratacao(item_categoria_id);
        CREATE INDEX IF NOT EXISTS idx_itens_valor ON itens_contratacao(valor_total);
        CREATE INDEX IF NOT EXISTS idx_itens_material_servico ON itens_contratacao(material_ou_servico);
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'itens_contratacao' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'itens_contratacao': {e}")
            raise
    
    def create_classificacoes_itens_table(self):
        """4. TABELA CLASSIFICACOES_ITENS (Classificação ML dos itens)"""
        sql = """
        CREATE TABLE IF NOT EXISTS classificacoes_itens (
            id BIGSERIAL PRIMARY KEY,
            
            -- Identificação
            numero_controle_pncp TEXT NOT NULL,
            numero_item TEXT NOT NULL,
            id_item_contratacao TEXT,
            
            -- Descrição e tipo
            descricao TEXT,
            item_type TEXT,
            
            -- Top 5 classificações
            top_1 TEXT,
            top_2 TEXT,
            top_3 TEXT,
            top_4 TEXT,
            top_5 TEXT,
            
            -- Scores das classificações
            score_1 DECIMAL(5,4),
            score_2 DECIMAL(5,4),
            score_3 DECIMAL(5,4),
            score_4 DECIMAL(5,4),
            score_5 DECIMAL(5,4),
            
            -- Confiança geral
            confidence DECIMAL(5,4),
            
            -- Metadados
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            
            -- Constraints
            UNIQUE(numero_controle_pncp, numero_item),
            FOREIGN KEY (numero_controle_pncp) REFERENCES contratacoes(numero_controle_pncp)
        );
        
        -- Índices para classificacoes_itens
        CREATE INDEX IF NOT EXISTS idx_classificacoes_numero_controle ON classificacoes_itens(numero_controle_pncp);
        CREATE INDEX IF NOT EXISTS idx_classificacoes_numero_item ON classificacoes_itens(numero_item);
        CREATE INDEX IF NOT EXISTS idx_classificacoes_confidence ON classificacoes_itens(confidence);
        CREATE INDEX IF NOT EXISTS idx_classificacoes_top1 ON classificacoes_itens(top_1);
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'classificacoes_itens' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'classificacoes_itens': {e}")
            raise
    
    def create_categorias_table(self):
        """5. TABELA CATEGORIAS (Categorias de produtos)"""
        sql = """
        CREATE TABLE IF NOT EXISTS categorias (
            id BIGSERIAL PRIMARY KEY,
            
            -- Código da categoria (chave principal)
            codigo_categoria TEXT UNIQUE NOT NULL,
            nome_categoria TEXT,
            
            -- Hierarquia de categorias (4 níveis)
            codigo_nivel_0 TEXT,
            nome_nivel_0 TEXT,
            codigo_nivel_1 TEXT,
            nome_nivel_1 TEXT,
            codigo_nivel_2 TEXT,
            nome_nivel_2 TEXT,
            codigo_nivel_3 TEXT,
            nome_nivel_3 TEXT,
            
            -- Metadados
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Índices para categorias
        CREATE INDEX IF NOT EXISTS idx_categorias_codigo ON categorias(codigo_categoria);
        CREATE INDEX IF NOT EXISTS idx_categorias_nome ON categorias(nome_categoria);
        CREATE INDEX IF NOT EXISTS idx_categorias_nivel0 ON categorias(codigo_nivel_0);
        CREATE INDEX IF NOT EXISTS idx_categorias_nivel1 ON categorias(codigo_nivel_1);
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'categorias' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'categorias': {e}")
            raise
    
    def create_atas_table(self):
        """6. TABELA ATAS (NOVO - Atas de Registro de Preço)"""
        sql = """
        CREATE TABLE IF NOT EXISTS atas (
            id BIGSERIAL PRIMARY KEY,
            
            -- Identificação
            numero_controle_pncp_compra TEXT NOT NULL,
            numero_ata_registro_preco TEXT NOT NULL,
            ano_ata INTEGER,
            sequencial_ata INTEGER,
            
            -- Datas da ata
            data_assinatura TIMESTAMPTZ,
            data_vigencia_inicio TIMESTAMPTZ,
            data_vigencia_fim TIMESTAMPTZ,
            data_inclusao TIMESTAMPTZ,
            data_atualizacao TIMESTAMPTZ,
            
            -- Status da ata
            situacao_ata TEXT,
            ativa BOOLEAN DEFAULT true,
            
            -- Órgão gerenciador
            orgao_gerenciador_cnpj TEXT,
            orgao_gerenciador_razao_social TEXT,
            unidade_gerenciadora_codigo TEXT,
            unidade_gerenciadora_nome TEXT,
            
            -- Informações da ata
            objeto_ata TEXT,
            observacoes TEXT,
            valor_estimado_total DECIMAL(15,2),
            
            -- Fornecedores participantes (JSONB para flexibilidade)
            fornecedores JSONB,
            
            -- Itens da ata (JSONB para flexibilidade)
            itens_ata JSONB,
            
            -- Documentos associados
            documentos JSONB,
            
            -- Metadados
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            
            -- Constraints
            UNIQUE(numero_controle_pncp_compra, numero_ata_registro_preco),
            FOREIGN KEY (numero_controle_pncp_compra) REFERENCES contratacoes(numero_controle_pncp)
        );
        
        -- Índices para atas
        CREATE INDEX IF NOT EXISTS idx_atas_numero_controle_compra ON atas(numero_controle_pncp_compra);
        CREATE INDEX IF NOT EXISTS idx_atas_numero_ata ON atas(numero_ata_registro_preco);
        CREATE INDEX IF NOT EXISTS idx_atas_ano ON atas(ano_ata);
        CREATE INDEX IF NOT EXISTS idx_atas_situacao ON atas(situacao_ata);
        CREATE INDEX IF NOT EXISTS idx_atas_ativa ON atas(ativa);
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'atas' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'atas': {e}")
            raise
    
    def create_pcas_table(self):
        """7. TABELA PCAS (NOVO - Planos de Contratações)"""
        sql = """
        CREATE TABLE IF NOT EXISTS pcas (
            id BIGSERIAL PRIMARY KEY,
            
            -- Identificação
            orgao_cnpj TEXT NOT NULL,
            codigo_unidade TEXT NOT NULL,
            ano_pca INTEGER NOT NULL,
            sequencial_pca INTEGER,
            
            -- Dados da unidade
            unidade_nome TEXT,
            unidade_municipio TEXT,
            unidade_uf TEXT,
            
            -- Status do PCA
            status_pca TEXT,
            data_aprovacao TIMESTAMPTZ,
            data_publicacao TIMESTAMPTZ,
            data_inclusao TIMESTAMPTZ,
            data_atualizacao TIMESTAMPTZ,
            
            -- Valores consolidados
            valor_total_estimado DECIMAL(15,2),
            quantidade_itens INTEGER,
            
            -- Itens do plano (JSONB para flexibilidade)
            itens_plano JSONB,
            
            -- Observações e justificativas
            observacoes TEXT,
            justificativa TEXT,
            
            -- Metadados
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            
            -- Constraints
            UNIQUE(orgao_cnpj, codigo_unidade, ano_pca)
        );
        
        -- Índices para pcas
        CREATE INDEX IF NOT EXISTS idx_pcas_orgao_cnpj ON pcas(orgao_cnpj);
        CREATE INDEX IF NOT EXISTS idx_pcas_codigo_unidade ON pcas(codigo_unidade);
        CREATE INDEX IF NOT EXISTS idx_pcas_ano ON pcas(ano_pca);
        CREATE INDEX IF NOT EXISTS idx_pcas_status ON pcas(status_pca);
        CREATE INDEX IF NOT EXISTS idx_pcas_valor ON pcas(valor_total_estimado);
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                self.connection.commit()
                console.print("✅ Tabela 'pcas' criada com sucesso!")
        except Exception as e:
            console.print(f"❌ Erro ao criar tabela 'pcas': {e}")
            raise
    
    def create_additional_indexes_and_constraints(self):
        """Criar índices adicionais e constraints para performance"""
        sql = """
        -- Índices compostos para queries comuns
        CREATE INDEX IF NOT EXISTS idx_contratacoes_ano_uf ON contratacoes(ano_compra, unidade_orgao_municipio_uf_sigla);
        CREATE INDEX IF NOT EXISTS idx_contratos_ano_valor ON contratos(ano_contrato, valor_global);
        CREATE INDEX IF NOT EXISTS idx_itens_categoria_valor ON itens_contratacao(item_categoria_id, valor_total);
        
        -- Índices para busca de texto
        CREATE INDEX IF NOT EXISTS idx_contratacoes_objeto_gin ON contratacoes USING gin(to_tsvector('portuguese', objeto_compra));
        CREATE INDEX IF NOT EXISTS idx_contratos_objeto_gin ON contratos USING gin(to_tsvector('portuguese', objeto_contrato));
        CREATE INDEX IF NOT EXISTS idx_itens_descricao_gin ON itens_contratacao USING gin(to_tsvector('portuguese', descricao));
        
        -- Índices para dados JSONB
        CREATE INDEX IF NOT EXISTS idx_atas_fornecedores_gin ON atas USING gin(fornecedores);
        CREATE INDEX IF NOT EXISTS idx_atas_itens_gin ON atas USING gin(itens_ata);
        CREATE INDEX IF NOT EXISTS idx_pcas_itens_gin ON pcas USING gin(itens_plano);
        
        -- Função de atualização automática de updated_at
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        -- Triggers para atualização automática
        CREATE TRIGGER update_contratacoes_updated_at BEFORE UPDATE ON contratacoes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        CREATE TRIGGER update_contratos_updated_at BEFORE UPDATE ON contratos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        CREATE TRIGGER update_itens_updated_at BEFORE UPDATE ON itens_contratacao FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        CREATE TRIGGER update_classificacoes_updated_at BEFORE UPDATE ON classificacoes_itens FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        CREATE TRIGGER update_categorias_updated_at BEFORE UPDATE ON categorias FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        CREATE TRIGGER update_atas_updated_at BEFORE UPDATE ON atas FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        CREATE TRIGGER update_pcas_updated_at BEFORE UPDATE ON pcas FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
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
            "Criando 7 tabelas específicas no Supabase:\n"
            "1. contratacoes (Compras/Editais/Avisos)\n"
            "2. contratos (Contratos firmados)\n"
            "3. itens_contratacao (Itens das contratações)\n"
            "4. classificacoes_itens (Classificação ML)\n"
            "5. categorias (Categorias de produtos)\n"
            "6. atas (Atas de Registro de Preço) [NOVO]\n"
            "7. pcas (Planos de Contratações) [NOVO]",
            title="🚀 Setup Database"
        ))
        
        if not self.connect():
            return False
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                
                task = progress.add_task("Criando tabelas...", total=8)
                
                progress.update(task, description="Criando tabela contratacoes...")
                self.create_contratacoes_table()
                progress.advance(task)
                
                progress.update(task, description="Criando tabela contratos...")
                self.create_contratos_table()
                progress.advance(task)
                
                progress.update(task, description="Criando tabela itens_contratacao...")
                self.create_itens_contratacao_table()
                progress.advance(task)
                
                progress.update(task, description="Criando tabela classificacoes_itens...")
                self.create_classificacoes_itens_table()
                progress.advance(task)
                
                progress.update(task, description="Criando tabela categorias...")
                self.create_categorias_table()
                progress.advance(task)
                
                progress.update(task, description="Criando tabela atas...")
                self.create_atas_table()
                progress.advance(task)
                
                progress.update(task, description="Criando tabela pcas...")
                self.create_pcas_table()
                progress.advance(task)
                
                progress.update(task, description="Criando índices e triggers...")
                self.create_additional_indexes_and_constraints()
                progress.advance(task)
            
            console.print("\n🎉 [bold green]Setup do banco de dados concluído com sucesso![/bold green]")
            
            # Exibir resumo das tabelas criadas
            table = Table(title="📊 Tabelas Criadas")
            table.add_column("Tabela", style="cyan", no_wrap=True)
            table.add_column("Tipo", style="magenta")
            table.add_column("Descrição", style="green")
            
            table.add_row("contratacoes", "Principal", "Compras/Editais/Avisos do PNCP")
            table.add_row("contratos", "Relacionada", "Contratos firmados")
            table.add_row("itens_contratacao", "Relacionada", "Itens das contratações")
            table.add_row("classificacoes_itens", "ML", "Classificação automática dos itens")
            table.add_row("categorias", "Referência", "Categorias de produtos")
            table.add_row("atas", "NOVA", "Atas de Registro de Preço")
            table.add_row("pcas", "NOVA", "Planos de Contratações")
            
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
