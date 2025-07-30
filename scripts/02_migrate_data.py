#!/usr/bin/env python3
"""
GovGo V1 - Migração de Dados V0 → V1
=====================================
Migra dados seletivos do V0 para V1 seguindo estratégia de embeddings

ESTRATÉGIA:
1. Categorias: DBL → V1 
2. Embeddings: V0 → V1 (contratacoes_embeddings → contratacao_emb)
3. Contratações: DBL → V1 (apenas os que têm embeddings)
4. Itens Contratação: DBL → V1 (apenas os que têm embeddings) 
5. Itens Classificação: DBL → V1 (apenas os que têm embeddings)

FONTES:
- DBL: PNCP_DB_v2.db (SQLite Local)
- V0: SUPABASE_v0 (Base antiga)
- V1: SUPABASE_v1 (Base nova)
"""

import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from dotenv import load_dotenv
import time
from typing import List, Dict, Any, Optional

# Carregar variáveis do .env
load_dotenv()

console = Console()

class DataMigrator:
    """Migrador de dados V0 → V1 com estratégia de embeddings"""
    
    def __init__(self):
        self.dbl_connection = None  # SQLite PNCP_DB_v2.db
        self.v0_connection = None   # Supabase V0
        self.v1_connection = None   # Supabase V1
        self.migration_stats = {
            'categorias': 0,
            'embeddings': 0,
            'contratacoes': 0,
            'itens_contratacao': 0,
            'itens_classificacao': 0,
            'errors': []
        }
        self.numerocontrolepncp_list = []  # Lista dos IDs com embeddings
        
    def connect_databases(self):
        """Conecta às três bases de dados"""
        try:
            # 1. Conectar ao SQLite Local (DBL)
            dbl_path = os.getenv("V0_SQLITE_PATH")
            if not os.path.exists(dbl_path):
                raise FileNotFoundError(f"SQLite não encontrado: {dbl_path}")
            
            self.dbl_connection = sqlite3.connect(dbl_path)
            self.dbl_connection.row_factory = sqlite3.Row
            console.print("✅ Conectado ao SQLite (DBL)")
            
            # 2. Conectar ao Supabase V0
            self.v0_connection = psycopg2.connect(
                host=os.getenv("SUPABASE_V0_HOST"),
                database=os.getenv("SUPABASE_V0_DBNAME"),
                user=os.getenv("SUPABASE_V0_USER"),
                password=os.getenv("SUPABASE_V0_PASSWORD"),
                port=int(os.getenv("SUPABASE_V0_PORT", "6543"))
            )
            console.print("✅ Conectado ao Supabase V0")
            
            # 3. Conectar ao Supabase V1
            self.v1_connection = psycopg2.connect(
                host=os.getenv("SUPABASE_HOST"),
                database=os.getenv("SUPABASE_DBNAME"),
                user=os.getenv("SUPABASE_USER"),
                password=os.getenv("SUPABASE_PASSWORD"),
                port=int(os.getenv("SUPABASE_PORT", "5432"))
            )
            console.print("✅ Conectado ao Supabase V1")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Erro ao conectar databases: {e}")
            return False
    
    def migrate_categorias(self):
        """ETAPA 1: Migrar categorias de DBL → V1"""
        console.print("\n🏷️ [bold blue]ETAPA 1: Migrando Categorias (DBL → V1)[/bold blue]")
        
        try:
            # Buscar categorias no SQLite
            cursor_dbl = self.dbl_connection.cursor()
            cursor_dbl.execute("""
                SELECT 
                    codCat,
                    nomCat,
                    codNv0,
                    nomNv0,
                    codNv1,
                    nomNv1,
                    codNv2,
                    nomNv2,
                    codNv3,
                    nomNv3
                FROM categoria
                ORDER BY codCat
            """)
            
            categorias = cursor_dbl.fetchall()
            total_categorias = len(categorias)
            console.print(f"📊 Encontradas {total_categorias} categorias no SQLite")
            
            if total_categorias == 0:
                console.print("⚠️ Nenhuma categoria encontrada no SQLite")
                return
            
            # Inserir no Supabase V1
            cursor_v1 = self.v1_connection.cursor()
            
            # Limpar tabela categoria primeiro
            cursor_v1.execute("DELETE FROM categoria;")
            console.print("🗑️ Tabela categoria limpa no V1")
            
            categorias_data = []
            for cat in categorias:
                categorias_data.append((
                    cat['codCat'],
                    cat['nomCat'],
                    cat['codNv0'],
                    cat['nomNv0'],
                    cat['codNv1'],
                    cat['nomNv1'],
                    cat['codNv2'],
                    cat['nomNv2'],
                    cat['codNv3'],
                    cat['nomNv3']
                ))
            
            # Insert em lotes
            execute_values(
                cursor_v1,
                """
                INSERT INTO categoria (
                    codcat, nomcat, codnv0, nomnv0, codnv1, nomnv1, 
                    codnv2, nomnv2, codnv3, nomnv3
                ) VALUES %s
                """,
                categorias_data,
                page_size=100
            )
            
            self.v1_connection.commit()
            self.migration_stats['categorias'] = total_categorias
            console.print(f"✅ {total_categorias} categorias migradas com sucesso!")
            
        except Exception as e:
            console.print(f"❌ Erro na migração de categorias: {e}")
            self.migration_stats['errors'].append(f"Categorias: {e}")
            self.v1_connection.rollback()
    
    def migrate_embeddings(self):
        """ETAPA 2: Migrar embeddings de V0 → V1 (contratacoes_embeddings → contratacao_emb)"""
        console.print("\n🧠 [bold blue]ETAPA 2: Migrando Embeddings (V0 → V1)[/bold blue]")
        
        try:
            # Descobrir o nome correto da tabela de embeddings
            cursor_v0 = self.v0_connection.cursor(cursor_factory=RealDictCursor)
            cursor_v0.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                AND table_name LIKE '%embedding%'
                ORDER BY table_name
            """)
            embedding_tables = [row['table_name'] for row in cursor_v0.fetchall()]
            
            if not embedding_tables:
                console.print("❌ Tabela de embeddings não encontrada no V0")
                return False
            
            embedding_table = embedding_tables[0]  # Usar a primeira tabela encontrada
            console.print(f"📊 Usando tabela: {embedding_table}")
            
            # Detectar nome correto da coluna de ID
            cursor_v0.execute(f"""
                SELECT column_name 
                FROM information_schema.columns
                WHERE table_name = '{embedding_table}'
                AND column_name IN ('numerocontrolepncp', 'numeroControlePNCP', 'numero_controle_pncp')
            """)
            id_columns = [row['column_name'] for row in cursor_v0.fetchall()]
            
            if not id_columns:
                console.print("❌ Coluna de ID não encontrada")
                return False
            
            id_column = id_columns[0]
            console.print(f"🔑 Usando coluna ID: {id_column}")
            
            # Verificar outras colunas disponíveis
            cursor_v0.execute(f"""
                SELECT column_name 
                FROM information_schema.columns
                WHERE table_name = '{embedding_table}'
                ORDER BY ordinal_position
            """)
            available_columns = [row['column_name'] for row in cursor_v0.fetchall()]
            console.print(f"📋 Colunas disponíveis: {', '.join(available_columns[:10])}...")
            
            # Buscar embeddings no V0 com colunas dinâmicas
            select_columns = [id_column]
            
            # Mapear colunas conhecidas
            column_mapping = {
                'embedding': ['embedding', 'embedding_vector', 'vector'],
                'modelo_embedding': ['modelo_embedding', 'model', 'modelo'],
                'metadata': ['metadata', 'meta'],
                'confidence': ['confidence', 'conf', 'score'],
                'created_at': ['created_at', 'data_criacao'],
                'updated_at': ['updated_at', 'data_atualizacao']
            }
            
            final_columns = [f"{id_column} as numerocontrolepncp"]
            
            for target_col, possible_names in column_mapping.items():
                found_col = None
                for possible in possible_names:
                    if possible in available_columns:
                        found_col = possible
                        break
                
                if found_col:
                    final_columns.append(f"{found_col} as {target_col}")
                else:
                    final_columns.append(f"NULL as {target_col}")
            
            # Buscar embeddings no V0
            cursor_v0.execute(f"""
                SELECT {', '.join(final_columns)}
                FROM {embedding_table}
                ORDER BY {id_column}
            """)
            
            embeddings = cursor_v0.fetchall()
            total_embeddings = len(embeddings)
            console.print(f"📊 Encontrados {total_embeddings} embeddings no V0")
            
            if total_embeddings == 0:
                console.print("⚠️ Nenhum embedding encontrado no V0")
                return
            
            # Limpar tabela contratacao_emb no V1
            cursor_v1 = self.v1_connection.cursor()
            cursor_v1.execute("DELETE FROM contratacao_emb;")
            console.print("🗑️ Tabela contratacao_emb limpa no V1")
            
            # Preparar dados para inserção
            embeddings_data = []
            numerocontrolepncp_set = set()
            
            for emb in embeddings:
                numerocontrolepncp_set.add(emb['numerocontrolepncp'])
                embeddings_data.append((
                    emb['numerocontrolepncp'],
                    emb['embedding_vector'],
                    emb['modelo_embedding'] or 'text-embedding-3-large',
                    emb['metadata'],
                    emb['confidence'],
                    emb['top_categories'],
                    emb['top_similarities'],
                    emb['created_at']
                ))
            
            # Guardar lista de IDs para próximas etapas
            self.numerocontrolepncp_list = list(numerocontrolepncp_set)
            console.print(f"📋 Lista de {len(self.numerocontrolepncp_list)} numeroControlePNCP coletada")
            
            # Insert em lotes
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task("Inserindo embeddings...", total=total_embeddings)
                
                batch_size = 50  # Menor por causa dos vectors
                for i in range(0, len(embeddings_data), batch_size):
                    batch = embeddings_data[i:i+batch_size]
                    
                    execute_values(
                        cursor_v1,
                        """
                        INSERT INTO contratacao_emb (
                            numerocontrolepncp, embedding_vector, modelo_embedding,
                            metadata, confidence, top_categories, top_similarities, created_at
                        ) VALUES %s
                        """,
                        batch,
                        page_size=batch_size
                    )
                    
                    progress.update(task, advance=len(batch))
                    
            self.v1_connection.commit()
            self.migration_stats['embeddings'] = total_embeddings
            console.print(f"✅ {total_embeddings} embeddings migrados com sucesso!")
            
        except Exception as e:
            console.print(f"❌ Erro na migração de embeddings: {e}")
            self.migration_stats['errors'].append(f"Embeddings: {e}")
            self.v1_connection.rollback()
    
    def migrate_contratacoes(self):
        """ETAPA 3: Migrar contratações de DBL → V1 (apenas os que têm embeddings)"""
        console.print("\n📋 [bold blue]ETAPA 3: Migrando Contratações Seletivas (DBL → V1)[/bold blue]")
        
        if not self.numerocontrolepncp_list:
            console.print("⚠️ Lista de numeroControlePNCP vazia. Pulando contratações.")
            return
        
        try:
            # Criar placeholders para o IN clause
            placeholders = ','.join(['?' for _ in self.numerocontrolepncp_list])
            
            # Buscar contratações no SQLite
            cursor_dbl = self.dbl_connection.cursor()
            query = f"""
                SELECT 
                    numeroControlePNCP,
                    modaDisputaId,
                    amparoLegal_codigo,
                    dataAberturaProposta,
                    dataEncerramentoProposta,
                    srp,
                    orgaoEntidade_cnpj,
                    orgaoEntidade_razaoSocial,
                    orgaoEntidade_poderId,
                    orgaoEntidade_esferaId,
                    anoCompra,
                    sequencialCompra,
                    processo,
                    objetoCompra,
                    valorTotalHomologado,
                    dataInclusao,
                    dataPublicacaoPNCP,
                    dataAtualizacao,
                    numeroCompra,
                    unidadeOrgao_ufNome,
                    unidadeOrgao_ufSigla,
                    unidadeOrgao_municipioNome,
                    unidadeOrgao_codigoUnidade,
                    unidadeOrgao_nomeUnidade,
                    unidadeOrgao_codigoIBGE,
                    modalidadeId,
                    dataAtualizacaoGlobal,
                    tipoInstrumentoConvocatoriocodigo,
                    valorTotalEstimado,
                    situacaoCompraId,
                    codCat,
                    score,
                    informacaoComplementar,
                    justificativaPresencial,
                    linkSistemaOrigem,
                    linkProcessoEletronico,
                    amparoLegal_nome,
                    amparoLegal_descricao,
                    modalidadeNome,
                    modaDisputaNome,
                    tipoInstrumentoConvocatorioNome,
                    situacaoCompraNome,
                    existeResultado,
                    orcamentoSigilosocodigo,
                    orcamentoSigioso_descricao,
                    orgaoSubrogado_cnpj,
                    orgaoSubrogado_razaoSocial,
                    orgaoSubrogado_poderId,
                    orgaoSubrogado_esferaId,
                    unidadeSubrogada_ufNome,
                    unidadeSubrogada_ufSigla,
                    unidadeSubrogada_municipioNome,
                    unidadeSubrogada_codigoUnidade,
                    unidadeSubrogada_nomeUnidade,
                    unidadeSubrogada_codigoIBGE,
                    usuarioNome,
                    fontesOrcamentarias
                FROM contratacao 
                WHERE numeroControlePNCP IN ({placeholders})
                ORDER BY numeroControlePNCP
            """
            
            cursor_dbl.execute(query, self.numerocontrolepncp_list)
            contratacoes = cursor_dbl.fetchall()
            total_contratacoes = len(contratacoes)
            
            console.print(f"📊 Encontradas {total_contratacoes} contratações no SQLite com embeddings")
            
            if total_contratacoes == 0:
                console.print("⚠️ Nenhuma contratação encontrada")
                return
            
            # Limpar tabela contratacao no V1
            cursor_v1 = self.v1_connection.cursor()
            cursor_v1.execute("DELETE FROM contratacao;")
            console.print("🗑️ Tabela contratacao limpa no V1")
            
            # Preparar dados (mapeando CamelCase → minúsculas)
            contratacoes_data = []
            for cont in contratacoes:
                contratacoes_data.append((
                    cont['numeroControlePNCP'],
                    cont['modaDisputaId'],
                    cont['amparoLegal_codigo'],
                    cont['dataAberturaProposta'],
                    cont['dataEncerramentoProposta'],
                    cont['srp'],
                    cont['orgaoEntidade_cnpj'],
                    cont['orgaoEntidade_razaoSocial'],
                    cont['orgaoEntidade_poderId'],
                    cont['orgaoEntidade_esferaId'],
                    cont['anoCompra'],
                    cont['sequencialCompra'],
                    cont['processo'],
                    cont['objetoCompra'],
                    cont['valorTotalHomologado'],
                    cont['dataInclusao'],
                    cont['dataPublicacaoPNCP'],
                    cont['dataAtualizacao'],
                    cont['numeroCompra'],
                    cont['unidadeOrgao_ufNome'],
                    cont['unidadeOrgao_ufSigla'],
                    cont['unidadeOrgao_municipioNome'],
                    cont['unidadeOrgao_codigoUnidade'],
                    cont['unidadeOrgao_nomeUnidade'],
                    cont['unidadeOrgao_codigoIBGE'],
                    cont['modalidadeId'],
                    cont['dataAtualizacaoGlobal'],
                    cont['tipoInstrumentoConvocatoriocodigo'],
                    cont['valorTotalEstimado'],
                    cont['situacaoCompraId'],
                    cont['codCat'],
                    cont['score'],
                    cont['informacaoComplementar'],
                    cont['justificativaPresencial'],
                    cont['linkSistemaOrigem'],
                    cont['linkProcessoEletronico'],
                    cont['amparoLegal_nome'],
                    cont['amparoLegal_descricao'],
                    cont['modalidadeNome'],
                    cont['modaDisputaNome'],
                    cont['tipoInstrumentoConvocatorioNome'],
                    cont['situacaoCompraNome'],
                    cont['existeResultado'],
                    cont['orcamentoSigilosocodigo'],
                    cont['orcamentoSigioso_descricao'],
                    cont['orgaoSubrogado_cnpj'],
                    cont['orgaoSubrogado_razaoSocial'],
                    cont['orgaoSubrogado_poderId'],
                    cont['orgaoSubrogado_esferaId'],
                    cont['unidadeSubrogada_ufNome'],
                    cont['unidadeSubrogada_ufSigla'],
                    cont['unidadeSubrogada_municipioNome'],
                    cont['unidadeSubrogada_codigoUnidade'],
                    cont['unidadeSubrogada_nomeUnidade'],
                    cont['unidadeSubrogada_codigoIBGE'],
                    cont['usuarioNome'],
                    cont['fontesOrcamentarias']
                ))
            
            # Insert em lotes com progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task("Inserindo contratações...", total=total_contratacoes)
                
                batch_size = 100
                for i in range(0, len(contratacoes_data), batch_size):
                    batch = contratacoes_data[i:i+batch_size]
                    
                    execute_values(
                        cursor_v1,
                        """
                        INSERT INTO contratacao (
                            numerocontrolepncp, modadisputaid, amparolegal_codigo, dataaberturaproposta,
                            dataencerramentoproposta, srp, orgaoentidade_cnpj, orgaoentidade_razaosocial,
                            orgaoentidade_poderid, orgaoentidade_esferaid, anocompra, sequencialcompra,
                            processo, objetocompra, valortotalhomologado, datainclusao, datapublicacaopncp,
                            dataatualizacao, numerocompra, unidadeorgao_ufnome, unidadeorgao_ufsigla,
                            unidadeorgao_municipionome, unidadeorgao_codigounidade, unidadeorgao_nomeunidade,
                            unidadeorgao_codigoibge, modalidadeid, dataatualizacaoglobal,
                            tipoinstrumentoconvocatoriocodigo, valortotalestimado, situacaocompraid,
                            codcat, score, informacaocomplementar, justificativapresencial,
                            linksistemaorigem, linkprocessoeletronico, amparolegal_nome,
                            amparolegal_descricao, modalidadenome, modadisputanome,
                            tipoinstrumentoconvocatorionome, situacaocompranome, existeresultado,
                            orcamentosigilosocodigo, orcamentosigioso_descricao, orgaosurogado_cnpj,
                            orgaosurogado_razaosocial, orgaosurogado_poderid, orgaosurogado_esferaid,
                            unidadesurogada_ufnome, unidadesurogada_ufsigla, unidadesurogada_municipionome,
                            unidadesurogada_codigounidade, unidadesurogada_nomeunidade,
                            unidadesurogada_codigoibge, usuarionome, fontesorcamentarias
                        ) VALUES %s
                        """,
                        batch,
                        page_size=batch_size
                    )
                    
                    progress.update(task, advance=len(batch))
            
            self.v1_connection.commit()
            self.migration_stats['contratacoes'] = total_contratacoes
            console.print(f"✅ {total_contratacoes} contratações migradas com sucesso!")
            
        except Exception as e:
            console.print(f"❌ Erro na migração de contratações: {e}")
            self.migration_stats['errors'].append(f"Contratações: {e}")
            self.v1_connection.rollback()
    
    def migrate_itens_contratacao(self):
        """ETAPA 4: Migrar itens de contratação de DBL → V1 (apenas os que têm embeddings)"""
        console.print("\n📦 [bold blue]ETAPA 4: Migrando Itens Contratação (DBL → V1)[/bold blue]")
        
        if not self.numerocontrolepncp_list:
            console.print("⚠️ Lista de numeroControlePNCP vazia. Pulando itens.")
            return
        
        try:
            # Criar placeholders para o IN clause
            placeholders = ','.join(['?' for _ in self.numerocontrolepncp_list])
            
            # Buscar itens no SQLite
            cursor_dbl = self.dbl_connection.cursor()
            query = f"""
                SELECT 
                    numeroControlePNCP,
                    numeroItem,
                    descricao,
                    materialOuServico,
                    valorUnitarioEstimado,
                    valorTotal,
                    quantidade,
                    unidadeMedida,
                    itemCategoriaId,
                    itemCategoriaNome,
                    criterioJulgamentoId,
                    situacaoCompraItem,
                    tipoBeneficio,
                    dataInclusao,
                    dataAtualizacao,
                    ncmNbscodigo,
                    catalogo
                FROM item_contratacao 
                WHERE numeroControlePNCP IN ({placeholders})
                ORDER BY numeroControlePNCP, numeroItem
            """
            
            cursor_dbl.execute(query, self.numerocontrolepncp_list)
            itens = cursor_dbl.fetchall()
            total_itens = len(itens)
            
            console.print(f"📊 Encontrados {total_itens} itens de contratação no SQLite com embeddings")
            
            if total_itens == 0:
                console.print("⚠️ Nenhum item encontrado")
                return
            
            # Limpar tabela item_contratacao no V1
            cursor_v1 = self.v1_connection.cursor()
            cursor_v1.execute("DELETE FROM item_contratacao;")
            console.print("🗑️ Tabela item_contratacao limpa no V1")
            
            # Preparar dados (mapeando CamelCase → minúsculas)
            itens_data = []
            for item in itens:
                itens_data.append((
                    item['numeroControlePNCP'],
                    item['numeroItem'],
                    item['descricao'],
                    item['materialOuServico'],
                    item['valorUnitarioEstimado'],
                    item['valorTotal'],
                    item['quantidade'],
                    item['unidadeMedida'],
                    item['itemCategoriaId'],
                    item['itemCategoriaNome'],
                    item['criterioJulgamentoId'],
                    item['situacaoCompraItem'],
                    item['tipoBeneficio'],
                    item['dataInclusao'],
                    item['dataAtualizacao'],
                    item['ncmNbscodigo'],
                    item['catalogo']
                ))
            
            # Insert em lotes com progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task("Inserindo itens...", total=total_itens)
                
                batch_size = 100
                for i in range(0, len(itens_data), batch_size):
                    batch = itens_data[i:i+batch_size]
                    
                    execute_values(
                        cursor_v1,
                        """
                        INSERT INTO item_contratacao (
                            numerocontrolepncp, numeroitem, descricao, materialouservico,
                            valorunitarioestimado, valortotal, quantidade, unidademedida,
                            itemcategoriaid, itemcategorianome, criteriojulgamentoid,
                            situacaocompraitem, tipobeneficio, datainclusao, dataatualizacao,
                            ncmnbscodigo, catalogo
                        ) VALUES %s
                        """,
                        batch,
                        page_size=batch_size
                    )
                    
                    progress.update(task, advance=len(batch))
            
            self.v1_connection.commit()
            self.migration_stats['itens_contratacao'] = total_itens
            console.print(f"✅ {total_itens} itens de contratação migrados com sucesso!")
            
        except Exception as e:
            console.print(f"❌ Erro na migração de itens: {e}")
            self.migration_stats['errors'].append(f"Itens Contratação: {e}")
            self.v1_connection.rollback()
    
    def migrate_itens_classificacao(self):
        """ETAPA 5: Migrar classificações de itens de DBL → V1 (apenas os que têm embeddings)"""
        console.print("\n🏷️ [bold blue]ETAPA 5: Migrando Classificações Itens (DBL → V1)[/bold blue]")
        
        if not self.numerocontrolepncp_list:
            console.print("⚠️ Lista de numeroControlePNCP vazia. Pulando classificações.")
            return
        
        try:
            # Primeiro, buscar os IDs dos itens migrados para mapear as FKs
            cursor_v1 = self.v1_connection.cursor(cursor_factory=RealDictCursor)
            cursor_v1.execute("""
                SELECT id_item_contratacao, numerocontrolepncp, numeroitem
                FROM item_contratacao
                ORDER BY numerocontrolepncp, numeroitem
            """)
            
            itens_v1 = cursor_v1.fetchall()
            item_map = {}  # (numerocontrolepncp, numeroitem) -> id_item_contratacao
            
            for item in itens_v1:
                key = (item['numerocontrolepncp'], item['numeroitem'])
                item_map[key] = item['id_item_contratacao']
            
            console.print(f"📋 Mapeamento de {len(item_map)} itens para FKs criado")
            
            # Criar placeholders para o IN clause
            placeholders = ','.join(['?' for _ in self.numerocontrolepncp_list])
            
            # Buscar classificações no SQLite
            cursor_dbl = self.dbl_connection.cursor()
            query = f"""
                SELECT 
                    numeroControlePNCP,
                    numeroItem,
                    codigoClasse,
                    nomeClasse,
                    codigoPDP,
                    descricaoPDP,
                    tipoClassificacao,
                    nivelClassificacao
                FROM item_classificacao 
                WHERE numeroControlePNCP IN ({placeholders})
                ORDER BY numeroControlePNCP, numeroItem
            """
            
            cursor_dbl.execute(query, self.numerocontrolepncp_list)
            classificacoes = cursor_dbl.fetchall()
            total_classificacoes = len(classificacoes)
            
            console.print(f"📊 Encontradas {total_classificacoes} classificações no SQLite com embeddings")
            
            if total_classificacoes == 0:
                console.print("⚠️ Nenhuma classificação encontrada")
                return
            
            # Limpar tabela item_classificacao no V1
            cursor_v1 = self.v1_connection.cursor()
            cursor_v1.execute("DELETE FROM item_classificacao;")
            console.print("🗑️ Tabela item_classificacao limpa no V1")
            
            # Preparar dados com mapeamento de FKs
            classificacoes_data = []
            skipped = 0
            
            for classif in classificacoes:
                key = (classif['numeroControlePNCP'], classif['numeroItem'])
                
                if key in item_map:
                    classificacoes_data.append((
                        item_map[key],  # id_item_contratacao (FK)
                        classif['numeroControlePNCP'],
                        classif['numeroItem'],
                        classif['codigoClasse'],
                        classif['nomeClasse'],
                        classif['codigoPDP'],
                        classif['descricaoPDP'],
                        classif['tipoClassificacao'],
                        classif['nivelClassificacao']
                    ))
                else:
                    skipped += 1
            
            if skipped > 0:
                console.print(f"⚠️ {skipped} classificações puladas (item não encontrado)")
            
            # Insert em lotes com progress
            if classificacoes_data:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console
                ) as progress:
                    
                    task = progress.add_task("Inserindo classificações...", total=len(classificacoes_data))
                    
                    batch_size = 100
                    for i in range(0, len(classificacoes_data), batch_size):
                        batch = classificacoes_data[i:i+batch_size]
                        
                        execute_values(
                            cursor_v1,
                            """
                            INSERT INTO item_classificacao (
                                id_item_contratacao, numerocontrolepncp, numeroitem,
                                codigoclasse, nomeclasse, codigopdp, descricaopdp,
                                tipoclassificacao, nivelclassificacao
                            ) VALUES %s
                            """,
                            batch,
                            page_size=batch_size
                        )
                        
                        progress.update(task, advance=len(batch))
                
                self.v1_connection.commit()
                self.migration_stats['itens_classificacao'] = len(classificacoes_data)
                console.print(f"✅ {len(classificacoes_data)} classificações migradas com sucesso!")
            else:
                console.print("⚠️ Nenhuma classificação válida para migrar")
            
        except Exception as e:
            console.print(f"❌ Erro na migração de classificações: {e}")
            self.migration_stats['errors'].append(f"Classificações: {e}")
            self.v1_connection.rollback()
    
    def generate_migration_report(self):
        """Gerar relatório da migração"""
        console.print("\n📊 [bold green]RELATÓRIO DA MIGRAÇÃO[/bold green]")
        
        # Tabela de estatísticas
        table = Table(title="📈 Estatísticas de Migração")
        table.add_column("Etapa", style="cyan", no_wrap=True)
        table.add_column("Registros Migrados", style="magenta", justify="right")
        table.add_column("Status", style="green")
        
        for key, value in self.migration_stats.items():
            if key != 'errors':
                status = "✅ Sucesso" if value > 0 else "⚠️ Vazio"
                table.add_row(key.replace('_', ' ').title(), str(value), status)
        
        console.print(table)
        
        # Erros
        if self.migration_stats['errors']:
            console.print("\n❌ [bold red]ERROS ENCONTRADOS:[/bold red]")
            for error in self.migration_stats['errors']:
                console.print(f"  • {error}")
        else:
            console.print("\n✅ [bold green]Migração concluída sem erros![/bold green]")
        
        # Resumo
        total_migrated = sum(v for k, v in self.migration_stats.items() if k != 'errors')
        console.print(f"\n🎉 [bold blue]Total de registros migrados: {total_migrated}[/bold blue]")
        console.print(f"📋 [bold blue]IDs com embeddings: {len(self.numerocontrolepncp_list)}[/bold blue]")
    
    def run_migration(self):
        """Executar migração completa"""
        console.print(Panel.fit(
            "[bold blue]GovGo V1 - Migração de Dados[/bold blue]\n"
            "Estratégia: Embeddings → Dados Seletivos\n\n"
            "📋 DBL (SQLite) → V1 (Supabase)\n"
            "🧠 V0 (Supabase) → V1 (Supabase)\n\n"
            "1. Categorias (DBL → V1)\n"
            "2. Embeddings (V0 → V1)\n"
            "3. Contratações seletivas (DBL → V1)\n"
            "4. Itens seletivos (DBL → V1)\n"
            "5. Classificações seletivas (DBL → V1)",
            title="🔄 Migração V0 → V1"
        ))
        
        start_time = time.time()
        
        # Conectar databases
        if not self.connect_databases():
            return False
        
        try:
            # Progress geral da migração (5 etapas)
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Progresso Geral:[/bold blue] [progress.description]"),
                BarColumn(),
                TaskProgressColumn(),
                TextColumn("[bold green]{task.completed}/{task.total} etapas[/bold green]"),
                console=console
            ) as overall_progress:
                
                main_task = overall_progress.add_task(
                    "Iniciando migração...", 
                    total=5
                )
                
                # Etapa 1: Categorias
                overall_progress.update(main_task, description="📂 Migrando Categorias")
                self.migrate_categorias()
                overall_progress.update(main_task, advance=1, description="✅ Categorias concluídas")
                
                # Etapa 2: Embeddings
                overall_progress.update(main_task, description="🧠 Migrando Embeddings")
                self.migrate_embeddings()
                overall_progress.update(main_task, advance=1, description="✅ Embeddings concluídos")
                
                # Etapa 3: Contratações
                overall_progress.update(main_task, description="📋 Migrando Contratações")
                self.migrate_contratacoes()
                overall_progress.update(main_task, advance=1, description="✅ Contratações concluídas")
                
                # Etapa 4: Itens
                overall_progress.update(main_task, description="📦 Migrando Itens")
                self.migrate_itens_contratacao()
                overall_progress.update(main_task, advance=1, description="✅ Itens concluídos")
                
                # Etapa 5: Classificações
                overall_progress.update(main_task, description="🏷️ Migrando Classificações")
                self.migrate_itens_classificacao()
                overall_progress.update(main_task, advance=1, description="🎉 Migração concluída!")
            
            # Relatório final
            self.generate_migration_report()
            
            end_time = time.time()
            duration = end_time - start_time
            console.print(f"\n⏱️ [bold blue]Tempo total: {duration:.2f} segundos ({duration/60:.1f} minutos)[/bold blue]")
            
            return True
            
        except Exception as e:
            console.print(f"\n❌ [bold red]Erro crítico na migração: {e}[/bold red]")
            return False
        
        finally:
            # Fechar conexões
            if self.dbl_connection:
                self.dbl_connection.close()
                console.print("🔌 SQLite desconectado")
            
            if self.v0_connection:
                self.v0_connection.close()
                console.print("🔌 Supabase V0 desconectado")
            
            if self.v1_connection:
                self.v1_connection.close()
                console.print("🔌 Supabase V1 desconectado")

def main():
    """Função principal"""
    migrator = DataMigrator()
    
    if migrator.run_migration():
        console.print("\n✅ [bold green]Migração concluída com sucesso![/bold green]")
        console.print("🚀 Dados do V0 migrados para V1 seguindo estratégia de embeddings")
    else:
        console.print("\n❌ [bold red]Falha na migração[/bold red]")
        exit(1)

if __name__ == "__main__":
    main()
