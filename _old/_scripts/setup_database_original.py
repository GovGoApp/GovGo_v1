"""
GovGo V1 - Setup do Banco de Dados
==================================

Cria estrutura unificada no Supabase baseada nas tabelas existentes
do PNCP_DB_v2 e estrutura atual do Supabase.
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
    """Configurador do banco de dados unificado"""
    
    def __init__(self):
        self.connection = None
        
    def connect(self):
        """Conecta ao banco de dados"""
        try:
            self.connection = psycopg2.connect(config.database.supabase_db_url)
            console.print("[green]✓ Conectado ao Supabase[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Erro na conexão: {e}[/red]")
            return False
    
    def setup_extensions(self):
        """Configura extensões necessárias"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Configurando extensões...", total=2)
            
            try:
                cursor = self.connection.cursor()
                
                # Verificar e criar extensão pgvector
                cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
                if cursor.fetchone() is None:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    progress.console.print("[yellow]→ Extensão pgvector criada[/yellow]")
                else:
                    progress.console.print("[green]→ Extensão pgvector já existe[/green]")
                progress.advance(task)
                
                # Verificar e criar extensão uuid-ossp
                cursor.execute("SELECT * FROM pg_extension WHERE extname = 'uuid-ossp';")
                if cursor.fetchone() is None:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
                    progress.console.print("[yellow]→ Extensão uuid-ossp criada[/yellow]")
                else:
                    progress.console.print("[green]→ Extensão uuid-ossp já existe[/green]")
                progress.advance(task)
                
                self.connection.commit()
                cursor.close()
                console.print("[green]✓ Extensões configuradas[/green]")
                return True
                
            except Exception as e:
                console.print(f"[red]✗ Erro ao configurar extensões: {e}[/red]")
                self.connection.rollback()
                return False
    
    def create_main_table(self):
        """Cria tabela principal unificada"""
        console.print(Panel("[bold yellow]Criando Tabela Principal Unificada[/bold yellow]"))
        
        try:
            cursor = self.connection.cursor()
            
            # Tabela principal unificada - baseada na estrutura existente + expansões
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documentos_pncp (
                    -- Identificação Universal
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    numeroControlePNCP TEXT UNIQUE NOT NULL,
                    tipo_documento TEXT NOT NULL CHECK (tipo_documento IN ('contratacao', 'contrato', 'ata', 'pca')),
                    
                    -- Metadados Temporais
                    data_criacao TIMESTAMPTZ DEFAULT NOW(),
                    data_atualizacao TIMESTAMPTZ DEFAULT NOW(),
                    data_publicacao_pncp DATE,
                    data_inclusao_sistema DATE DEFAULT CURRENT_DATE,
                    ano_referencia INTEGER,
                    
                    -- Dados Principais (JSON Flexível - mantém estrutura original)
                    dados_principais JSONB NOT NULL,
                    
                    -- Busca Semântica (compatível com sistema atual)
                    texto_busca TEXT,
                    embedding VECTOR(3072), -- Mantém dimensão atual do sistema
                    
                    -- Categorização (compatível com PNCP_DB_v2)
                    categoria_codigo TEXT, -- CODCAT da estrutura original
                    categoria_score REAL,  -- SCORE da estrutura original
                    
                    -- Índices de Performance (extraídos dos dados principais)
                    orgao_cnpj TEXT,
                    unidade_codigo TEXT,
                    modalidade_id INTEGER,
                    valor_estimado DECIMAL(15,2),
                    valor_homologado DECIMAL(15,2),
                    situacao_codigo TEXT,
                    
                    -- Controle de Status
                    status_processamento TEXT DEFAULT 'pendente' 
                        CHECK (status_processamento IN ('pendente', 'processando', 'processado', 'erro')),
                    tentativas_processamento INTEGER DEFAULT 0,
                    erro_processamento TEXT,
                    
                    -- Particionamento por data (computed column)
                    particao_data DATE GENERATED ALWAYS AS (
                        COALESCE(data_publicacao_pncp, data_inclusao_sistema, CURRENT_DATE)
                    ) STORED
                );
            """)
            
            console.print("[green]→ Tabela documentos_pncp criada[/green]")
            
            # Criar índices otimizados
            indices = [
                ("idx_documentos_numero_controle", "numeroControlePNCP"),
                ("idx_documentos_tipo", "tipo_documento"),
                ("idx_documentos_particao", "particao_data"),
                ("idx_documentos_orgao_cnpj", "orgao_cnpj"),
                ("idx_documentos_modalidade", "modalidade_id"),
                ("idx_documentos_status", "status_processamento"),
                ("idx_documentos_categoria", "categoria_codigo"),
                ("idx_documentos_ano", "ano_referencia")
            ]
            
            for nome_indice, coluna in indices:
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS {nome_indice} 
                    ON documentos_pncp ({coluna});
                """)
                console.print(f"[blue]→ Índice {nome_indice} criado[/blue]")
            
            # Índice vetorial para busca semântica
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documentos_embedding 
                ON documentos_pncp 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
            console.print("[blue]→ Índice vetorial criado[/blue]")
            
            # Índice GIN para busca textual
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documentos_busca_textual 
                ON documentos_pncp 
                USING gin (to_tsvector('portuguese', texto_busca));
            """)
            console.print("[blue]→ Índice busca textual criado[/blue]")
            
            # Índice GIN para dados JSON
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documentos_dados_gin 
                ON documentos_pncp 
                USING gin (dados_principais);
            """)
            console.print("[blue]→ Índice dados JSON criado[/blue]")
            
            self.connection.commit()
            cursor.close()
            console.print("[green]✓ Tabela principal criada com sucesso[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]✗ Erro ao criar tabela principal: {e}[/red]")
            self.connection.rollback()
            return False
    
    def create_auxiliary_tables(self):
        """Cria tabelas auxiliares baseadas na estrutura original"""
        console.print(Panel("[bold yellow]Criando Tabelas Auxiliares[/bold yellow]"))
        
        try:
            cursor = self.connection.cursor()
            
            # Tabela de categorias - EXATAMENTE como no PNCP_DB_v2
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categorias (
                    CODCAT TEXT PRIMARY KEY,
                    NOMCAT TEXT,
                    CODNV0 TEXT,
                    NOMNV0 TEXT,
                    CODNV1 TEXT,
                    NOMNV1 TEXT,
                    CODNV2 TEXT,
                    NOMNV2 TEXT,
                    CODNV3 TEXT,
                    NOMNV3 TEXT
                );
            """)
            console.print("[green]→ Tabela categorias criada[/green]")
            
            # Tabela de órgãos e unidades (cache de dados frequentes)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orgaos_unidades (
                    cnpj TEXT PRIMARY KEY,
                    razao_social TEXT,
                    nome_fantasia TEXT,
                    poder_id TEXT,
                    esfera_id TEXT,
                    uf_sigla TEXT,
                    municipio_nome TEXT,
                    municipio_ibge TEXT,
                    codigo_unidade TEXT,
                    nome_unidade TEXT,
                    ultima_atualizacao TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            console.print("[green]→ Tabela orgaos_unidades criada[/green]")
            
            # Tabela de logs de processamento
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs_processamento (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    data_execucao TIMESTAMPTZ DEFAULT NOW(),
                    tipo_processamento TEXT,
                    documentos_processados INTEGER DEFAULT 0,
                    documentos_erro INTEGER DEFAULT 0,
                    tempo_execucao_segundos INTEGER DEFAULT 0,
                    detalhes JSONB
                );
            """)
            console.print("[green]→ Tabela logs_processamento criada[/green]")
            
            # Índices auxiliares
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orgaos_cnpj ON orgaos_unidades (cnpj);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_data ON logs_processamento (data_execucao);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_tipo ON logs_processamento (tipo_processamento);")
            
            self.connection.commit()
            cursor.close()
            console.print("[green]✓ Tabelas auxiliares criadas[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]✗ Erro ao criar tabelas auxiliares: {e}[/red]")
            self.connection.rollback()
            return False
    
    def create_search_functions(self):
        """Cria funções de busca compatíveis com sistema atual"""
        console.print(Panel("[bold yellow]Criando Funções de Busca[/bold yellow]"))
        
        try:
            cursor = self.connection.cursor()
            
            # Função de busca semântica - compatível com sistema atual
            cursor.execute("""
                CREATE OR REPLACE FUNCTION search_semantic_v1(
                    query_embedding VECTOR(3072),
                    p_limit INTEGER DEFAULT 20,
                    filter_tipo TEXT DEFAULT NULL,
                    filter_expired BOOLEAN DEFAULT TRUE
                )
                RETURNS TABLE (
                    numeroControlePNCP TEXT,
                    tipo_documento TEXT,
                    similarity FLOAT,
                    dados JSONB
                )
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    RETURN QUERY
                    SELECT
                        d.numeroControlePNCP,
                        d.tipo_documento,
                        1 - (d.embedding <=> query_embedding) as similarity,
                        d.dados_principais as dados
                    FROM
                        documentos_pncp d
                    WHERE 
                        d.embedding IS NOT NULL
                        AND d.status_processamento = 'processado'
                        AND (filter_tipo IS NULL OR d.tipo_documento = filter_tipo)
                        AND (NOT filter_expired OR 
                             (d.dados_principais->>'dataEncerramentoProposta')::date >= CURRENT_DATE OR
                             d.dados_principais->>'dataEncerramentoProposta' IS NULL)
                    ORDER BY
                        similarity DESC
                    LIMIT p_limit;
                END;
                $$;
            """)
            console.print("[green]→ Função search_semantic_v1 criada[/green]")
            
            # Função de busca textual
            cursor.execute("""
                CREATE OR REPLACE FUNCTION search_textual_v1(
                    query_text TEXT,
                    p_limit INTEGER DEFAULT 20,
                    filter_tipo TEXT DEFAULT NULL,
                    filter_expired BOOLEAN DEFAULT TRUE
                )
                RETURNS TABLE (
                    numeroControlePNCP TEXT,
                    tipo_documento TEXT,
                    rank_score FLOAT,
                    dados JSONB
                )
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    RETURN QUERY
                    SELECT
                        d.numeroControlePNCP,
                        d.tipo_documento,
                        ts_rank(to_tsvector('portuguese', d.texto_busca), plainto_tsquery('portuguese', query_text)) as rank_score,
                        d.dados_principais as dados
                    FROM
                        documentos_pncp d
                    WHERE 
                        to_tsvector('portuguese', d.texto_busca) @@ plainto_tsquery('portuguese', query_text)
                        AND d.status_processamento = 'processado'
                        AND (filter_tipo IS NULL OR d.tipo_documento = filter_tipo)
                        AND (NOT filter_expired OR 
                             (d.dados_principais->>'dataEncerramentoProposta')::date >= CURRENT_DATE OR
                             d.dados_principais->>'dataEncerramentoProposta' IS NULL)
                    ORDER BY
                        rank_score DESC
                    LIMIT p_limit;
                END;
                $$;
            """)
            console.print("[green]→ Função search_textual_v1 criada[/green]")
            
            # Função de migração de dados do sistema atual
            cursor.execute("""
                CREATE OR REPLACE FUNCTION migrate_contratacao_to_unified(
                    p_numeroControlePNCP TEXT,
                    p_dados_contratacao JSONB,
                    p_embedding VECTOR(3072) DEFAULT NULL,
                    p_categoria_codigo TEXT DEFAULT NULL,
                    p_categoria_score REAL DEFAULT NULL
                )
                RETURNS UUID
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    new_id UUID;
                BEGIN
                    INSERT INTO documentos_pncp (
                        numeroControlePNCP,
                        tipo_documento,
                        dados_principais,
                        embedding,
                        categoria_codigo,
                        categoria_score,
                        texto_busca,
                        orgao_cnpj,
                        modalidade_id,
                        valor_estimado,
                        valor_homologado,
                        ano_referencia,
                        status_processamento
                    ) VALUES (
                        p_numeroControlePNCP,
                        'contratacao',
                        p_dados_contratacao,
                        p_embedding,
                        p_categoria_codigo,
                        p_categoria_score,
                        p_dados_contratacao->>'descricaoCompleta',
                        p_dados_contratacao->>'orgaoEntidade_cnpj',
                        (p_dados_contratacao->>'modalidadeId')::INTEGER,
                        (p_dados_contratacao->>'valorTotalEstimado')::DECIMAL,
                        (p_dados_contratacao->>'valorTotalHomologado')::DECIMAL,
                        (p_dados_contratacao->>'anoCompra')::INTEGER,
                        CASE WHEN p_embedding IS NOT NULL THEN 'processado' ELSE 'pendente' END
                    )
                    ON CONFLICT (numeroControlePNCP) DO UPDATE SET
                        dados_principais = EXCLUDED.dados_principais,
                        embedding = COALESCE(EXCLUDED.embedding, documentos_pncp.embedding),
                        categoria_codigo = COALESCE(EXCLUDED.categoria_codigo, documentos_pncp.categoria_codigo),
                        categoria_score = COALESCE(EXCLUDED.categoria_score, documentos_pncp.categoria_score),
                        data_atualizacao = NOW()
                    RETURNING id INTO new_id;
                    
                    RETURN new_id;
                END;
                $$;
            """)
            console.print("[green]→ Função migrate_contratacao_to_unified criada[/green]")
            
            self.connection.commit()
            cursor.close()
            console.print("[green]✓ Funções de busca criadas[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]✗ Erro ao criar funções: {e}[/red]")
            self.connection.rollback()
            return False
    
    def verify_setup(self):
        """Verifica se a configuração foi bem-sucedida"""
        console.print(Panel("[bold yellow]Verificando Configuração[/bold yellow]"))
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            # Verificar tabelas
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('documentos_pncp', 'categorias', 'orgaos_unidades', 'logs_processamento')
                ORDER BY table_name;
            """)
            
            tabelas = [row['table_name'] for row in cursor.fetchall()]
            
            tabela_status = Table(title="Status das Tabelas")
            tabela_status.add_column("Tabela", style="cyan")
            tabela_status.add_column("Status", style="green")
            
            tabelas_esperadas = ['categorias', 'documentos_pncp', 'logs_processamento', 'orgaos_unidades']
            for tabela in tabelas_esperadas:
                status = "✓ Criada" if tabela in tabelas else "✗ Ausente"
                cor = "green" if tabela in tabelas else "red"
                tabela_status.add_row(tabela, f"[{cor}]{status}[/{cor}]")
            
            console.print(tabela_status)
            
            # Verificar extensões
            cursor.execute("SELECT extname FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp');")
            extensoes = [row['extname'] for row in cursor.fetchall()]
            
            console.print(f"\n[blue]Extensões:[/blue]")
            console.print(f"→ pgvector: {'✓' if 'vector' in extensoes else '✗'}")
            console.print(f"→ uuid-ossp: {'✓' if 'uuid-ossp' in extensoes else '✗'}")
            
            # Verificar funções
            cursor.execute("""
                SELECT routine_name 
                FROM information_schema.routines 
                WHERE routine_schema = 'public' 
                AND routine_name LIKE 'search_%_v1' OR routine_name LIKE 'migrate_%'
                ORDER BY routine_name;
            """)
            
            funcoes = [row['routine_name'] for row in cursor.fetchall()]
            console.print(f"\n[blue]Funções criadas: {len(funcoes)}[/blue]")
            for funcao in funcoes:
                console.print(f"→ {funcao}")
            
            cursor.close()
            
            if len(tabelas) == 4 and len(extensoes) == 2:
                console.print("\n[green]✓ Configuração concluída com sucesso![/green]")
                return True
            else:
                console.print("\n[red]✗ Configuração incompleta[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]✗ Erro na verificação: {e}[/red]")
            return False
    
    def close(self):
        """Fecha conexão"""
        if self.connection:
            self.connection.close()
            console.print("[blue]Conexão fechada[/blue]")

def main():
    """Função principal"""
    console.print(Panel.fit("[bold magenta]GovGo V1 - Setup do Banco de Dados[/bold magenta]"))
    
    # Verificar configuração
    try:
        config.validate()
        console.print("[green]✓ Configuração validada[/green]")
    except Exception as e:
        console.print(f"[red]✗ Erro na configuração: {e}[/red]")
        return False
    
    # Executar setup
    setup = DatabaseSetup()
    
    try:
        if not setup.connect():
            return False
        
        if not setup.setup_extensions():
            return False
        
        if not setup.create_main_table():
            return False
        
        if not setup.create_auxiliary_tables():
            return False
        
        if not setup.create_search_functions():
            return False
        
        if not setup.verify_setup():
            return False
        
        console.print(Panel("[bold green]🎉 Setup concluído com sucesso![/bold green]"))
        console.print("\n[yellow]Próximos passos:[/yellow]")
        console.print("1. Execute: python test_setup.py")
        console.print("2. Configure o pipeline: python govgo_v1_pipeline.py")
        console.print("3. Teste a busca: python govgo_v1_search.py")
        
        return True
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup interrompido pelo usuário[/yellow]")
        return False
    except Exception as e:
        console.print(f"\n[red]Erro no setup: {e}[/red]")
        return False
    finally:
        setup.close()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
