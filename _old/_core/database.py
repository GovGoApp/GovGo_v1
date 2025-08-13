"""
GovGo V1 - Gerenciador de Banco de Dados
========================================

Gerencia conexões e operações com o banco de dados Supabase,
compatível com a estrutura existente e sistema de busca atual.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2.pool import ThreadedConnectionPool
import numpy as np

from .config import config
from .models import DocumentoPNCP, ContratacaoSupabase, ResultadoBuscaCompativel

logger = logging.getLogger(__name__)


class SupabaseManager:
    """
    Gerenciador de conexões e operações com Supabase.
    Compatível com as estruturas existentes do sistema v0.
    """
    
    def __init__(self):
        self.pool = None
        self._initialize_connection_pool()
    
    def _initialize_connection_pool(self):
        """Inicializa o pool de conexões PostgreSQL."""
        try:
            database_url = config.get_database_url()
            
            self.pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=database_url
            )
            
            logger.info("Pool de conexões Supabase inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar pool de conexões: {e}")
            raise
    
    def get_connection(self):
        """Obtém uma conexão do pool."""
        if not self.pool:
            self._initialize_connection_pool()
        return self.pool.getconn()
    
    def return_connection(self, conn):
        """Retorna uma conexão para o pool."""
        if self.pool:
            self.pool.putconn(conn)
    
    def close_all_connections(self):
        """Fecha todas as conexões do pool."""
        if self.pool:
            self.pool.closeall()
            logger.info("Todas as conexões foram fechadas")
    
    # ========================================
    # OPERAÇÕES COMPATÍVEIS COM V0
    # ========================================
    
    def buscar_contratacoes(self, 
                           texto_busca: str = None,
                           embeddings: List[float] = None,
                           limite: int = 10,
                           threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Busca contratações compatível com gvg_search_utils_v3.py
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if embeddings:
                # Busca semântica (compatível com semantic_search)
                query = """
                SELECT c.*, 
                       ce.embedding <=> %s::vector as similarity
                FROM contratacoes c
                LEFT JOIN contratacoes_embeddings ce ON c.numerocontrolepncp = ce.numerocontrolepncp
                WHERE ce.embedding IS NOT NULL
                AND (ce.embedding <=> %s::vector) < %s
                ORDER BY similarity
                LIMIT %s;
                """
                cursor.execute(query, (embeddings, embeddings, 1 - threshold, limite))
                
            elif texto_busca:
                # Busca textual (compatível com keyword_search)
                query = """
                SELECT c.*, 0.0 as similarity
                FROM contratacoes c
                WHERE to_tsvector('portuguese', COALESCE(c.objeto, '') || ' ' || 
                                                COALESCE(c.unidadeorcamentaria_nome, '') || ' ' ||
                                                COALESCE(c.orgaoentidade_razaosocial, ''))
                      @@ plainto_tsquery('portuguese', %s)
                ORDER BY ts_rank(to_tsvector('portuguese', COALESCE(c.objeto, '') || ' ' || 
                                                          COALESCE(c.unidadeorcamentaria_nome, '') || ' ' ||
                                                          COALESCE(c.orgaoentidade_razaosocial, '')),
                                plainto_tsquery('portuguese', %s)) DESC
                LIMIT %s;
                """
                cursor.execute(query, (texto_busca, texto_busca, limite))
            
            else:
                # Busca geral
                query = "SELECT *, 0.0 as similarity FROM contratacoes ORDER BY created_at DESC LIMIT %s;"
                cursor.execute(query, (limite,))
            
            resultados = cursor.fetchall()
            
            # Converte RealDictRow para dict comum
            return [dict(row) for row in resultados]
            
        except Exception as e:
            logger.error(f"Erro na busca de contratações: {e}")
            return []
        finally:
            if conn:
                self.return_connection(conn)
    
    def inserir_contratacao(self, dados: Dict[str, Any]) -> bool:
        """
        Insere contratação compatível com estrutura existente.
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Campos obrigatórios da estrutura existente
            campos = [
                'numerocontrolepncp', 'objeto', 'orgaoentidade_cnpj', 
                'orgaoentidade_razaosocial', 'unidadeorcamentaria_codigo',
                'unidadeorcamentaria_nome', 'valorestimado', 'situacao',
                'modcompra', 'tipoprocedimento', 'justificativacontratacaodireta'
            ]
            
            # Prepara dados para inserção
            valores = []
            placeholders = []
            
            for campo in campos:
                if campo in dados:
                    valores.append(dados[campo])
                    placeholders.append('%s')
                else:
                    valores.append(None)
                    placeholders.append('%s')
            
            query = f"""
            INSERT INTO contratacoes ({', '.join(campos)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT (numerocontrolepncp) DO UPDATE SET
                objeto = EXCLUDED.objeto,
                orgaoentidade_razaosocial = EXCLUDED.orgaoentidade_razaosocial,
                updated_at = NOW()
            """
            
            cursor.execute(query, valores)
            conn.commit()
            
            logger.info(f"Contratação {dados.get('numerocontrolepncp', 'N/A')} inserida com sucesso")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Erro ao inserir contratação: {e}")
            return False
        finally:
            if conn:
                self.return_connection(conn)
    
    def inserir_embedding(self, numero_controle: str, embedding: List[float]) -> bool:
        """
        Insere embedding compatível com contratacoes_embeddings.
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            INSERT INTO contratacoes_embeddings (numerocontrolepncp, embedding)
            VALUES (%s, %s)
            ON CONFLICT (numerocontrolepncp) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                updated_at = NOW()
            """
            
            cursor.execute(query, (numero_controle, embedding))
            conn.commit()
            
            logger.debug(f"Embedding para {numero_controle} inserido com sucesso")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Erro ao inserir embedding: {e}")
            return False
        finally:
            if conn:
                self.return_connection(conn)
    
    # ========================================
    # OPERAÇÕES PARA NOVOS DOCUMENTOS (V1)
    # ========================================
    
    def inserir_documento_pncp(self, documento: DocumentoPNCP) -> bool:
        """
        Insere documento no novo modelo unificado V1.
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            INSERT INTO documentos_pncp (
                numero_controle_pncp, tipo_documento, dados_originais,
                objeto, orgao_cnpj, orgao_razao_social,
                unidade_codigo, unidade_nome, valor_estimado,
                situacao, modalidade, data_publicacao,
                status_processamento, embedding
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (numero_controle_pncp, tipo_documento) DO UPDATE SET
                dados_originais = EXCLUDED.dados_originais,
                objeto = EXCLUDED.objeto,
                updated_at = NOW()
            """
            
            cursor.execute(query, (
                documento.numero_controle_pncp,
                documento.tipo_documento,
                json.dumps(documento.dados_originais) if documento.dados_originais else None,
                documento.objeto,
                documento.orgao_cnpj,
                documento.orgao_razao_social,
                documento.unidade_codigo,
                documento.unidade_nome,
                documento.valor_estimado,
                documento.situacao,
                documento.modalidade,
                documento.data_publicacao,
                documento.status_processamento,
                documento.embedding
            ))
            
            conn.commit()
            
            logger.info(f"Documento {documento.numero_controle_pncp} ({documento.tipo_documento}) inserido")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Erro ao inserir documento PNCP: {e}")
            return False
        finally:
            if conn:
                self.return_connection(conn)
    
    def buscar_documentos_unificado(self,
                                  texto_busca: str = None,
                                  embedding: List[float] = None,
                                  tipos_documento: List[str] = None,
                                  limite: int = 10,
                                  threshold: float = 0.7) -> List[DocumentoPNCP]:
        """
        Busca unificada nos novos documentos V1.
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            where_conditions = ["status_processamento = 'processado'"]
            params = []
            
            if tipos_documento:
                where_conditions.append(f"tipo_documento = ANY(%s)")
                params.append(tipos_documento)
            
            if embedding:
                where_conditions.append("embedding IS NOT NULL")
                where_conditions.append(f"(embedding <=> %s::vector) < %s")
                params.extend([embedding, 1 - threshold])
                order_by = "embedding <=> %s::vector"
                params.append(embedding)
            
            elif texto_busca:
                where_conditions.append("""
                    to_tsvector('portuguese', COALESCE(objeto, '') || ' ' || 
                                            COALESCE(orgao_razao_social, '') || ' ' ||
                                            COALESCE(unidade_nome, ''))
                    @@ plainto_tsquery('portuguese', %s)
                """)
                params.append(texto_busca)
                order_by = """
                    ts_rank(to_tsvector('portuguese', COALESCE(objeto, '') || ' ' || 
                                                    COALESCE(orgao_razao_social, '') || ' ' ||
                                                    COALESCE(unidade_nome, '')),
                           plainto_tsquery('portuguese', %s)) DESC
                """
                params.append(texto_busca)
            else:
                order_by = "created_at DESC"
            
            query = f"""
            SELECT * FROM documentos_pncp
            WHERE {' AND '.join(where_conditions)}
            ORDER BY {order_by}
            LIMIT %s
            """
            params.append(limite)
            
            cursor.execute(query, params)
            resultados = cursor.fetchall()
            
            documentos = []
            for row in resultados:
                doc = DocumentoPNCP(
                    numero_controle_pncp=row['numero_controle_pncp'],
                    tipo_documento=row['tipo_documento'],
                    dados_originais=json.loads(row['dados_originais']) if row['dados_originais'] else {},
                    objeto=row['objeto'],
                    orgao_cnpj=row['orgao_cnpj'],
                    orgao_razao_social=row['orgao_razao_social'],
                    unidade_codigo=row['unidade_codigo'],
                    unidade_nome=row['unidade_nome'],
                    valor_estimado=row['valor_estimado'],
                    situacao=row['situacao'],
                    modalidade=row['modalidade'],
                    data_publicacao=row['data_publicacao'],
                    status_processamento=row['status_processamento'],
                    embedding=row['embedding']
                )
                documentos.append(doc)
            
            return documentos
            
        except Exception as e:
            logger.error(f"Erro na busca unificada: {e}")
            return []
        finally:
            if conn:
                self.return_connection(conn)
    
    # ========================================
    # CONVERSÃO E COMPATIBILIDADE
    # ========================================
    
    def converter_contratacao_para_documento(self, dados_contratacao: Dict[str, Any]) -> DocumentoPNCP:
        """
        Converte dados da estrutura antiga para o novo modelo.
        """
        return DocumentoPNCP(
            numero_controle_pncp=dados_contratacao.get('numerocontrolepncp'),
            tipo_documento='contratacao',
            dados_originais=dados_contratacao,
            objeto=dados_contratacao.get('objeto'),
            orgao_cnpj=dados_contratacao.get('orgaoentidade_cnpj'),
            orgao_razao_social=dados_contratacao.get('orgaoentidade_razaosocial'),
            unidade_codigo=dados_contratacao.get('unidadeorcamentaria_codigo'),
            unidade_nome=dados_contratacao.get('unidadeorcamentaria_nome'),
            valor_estimado=dados_contratacao.get('valorestimado'),
            situacao=dados_contratacao.get('situacao'),
            modalidade=dados_contratacao.get('modcompra'),
            data_publicacao=dados_contratacao.get('created_at'),
            status_processamento='processado'
        )
    
    def buscar_compativel_v0(self,
                           query: str,
                           embedding: List[float] = None,
                           search_type: str = 'hybrid',
                           limit: int = 10) -> List[ResultadoBuscaCompativel]:
        """
        Busca compatível com gvg_search_utils_v3.py retornando formato esperado.
        """
        try:
            if search_type == 'semantic' and embedding:
                resultados = self.buscar_contratacoes(embeddings=embedding, limite=limit)
            elif search_type == 'textual':
                resultados = self.buscar_contratacoes(texto_busca=query, limite=limit)
            else:  # hybrid
                # Primeiro busca semântica
                sem_results = []
                if embedding:
                    sem_results = self.buscar_contratacoes(embeddings=embedding, limite=limit//2)
                
                # Depois busca textual
                text_results = self.buscar_contratacoes(texto_busca=query, limite=limit//2)
                
                # Combina resultados
                resultados = sem_results + text_results
                
                # Remove duplicatas por numerocontrolepncp
                seen = set()
                resultados_unicos = []
                for r in resultados:
                    if r['numerocontrolepncp'] not in seen:
                        seen.add(r['numerocontrolepncp'])
                        resultados_unicos.append(r)
                
                resultados = resultados_unicos[:limit]
            
            # Converte para formato compatível
            resultados_compatíveis = []
            for r in resultados:
                resultado = ResultadoBuscaCompativel(
                    numerocontrolepncp=r.get('numerocontrolepncp'),
                    objeto=r.get('objeto'),
                    orgaoentidade_razaosocial=r.get('orgaoentidade_razaosocial'),
                    unidadeorcamentaria_nome=r.get('unidadeorcamentaria_nome'),
                    valorestimado=r.get('valorestimado'),
                    situacao=r.get('situacao'),
                    similarity=r.get('similarity', 0.0),
                    dados_completos=r
                )
                resultados_compatíveis.append(resultado)
            
            return resultados_compatíveis
            
        except Exception as e:
            logger.error(f"Erro na busca compatível: {e}")
            return []
    
    # ========================================
    # ESTATÍSTICAS E MANUTENÇÃO
    # ========================================
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do banco de dados.
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            stats = {}
            
            # Contratações (estrutura antiga)
            cursor.execute("SELECT COUNT(*) FROM contratacoes")
            stats['total_contratacoes'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM contratacoes_embeddings")
            stats['contratacoes_com_embedding'] = cursor.fetchone()[0]
            
            # Documentos PNCP (estrutura nova)
            try:
                cursor.execute("SELECT COUNT(*) FROM documentos_pncp")
                stats['total_documentos_pncp'] = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT tipo_documento, COUNT(*) 
                    FROM documentos_pncp 
                    GROUP BY tipo_documento
                """)
                stats['documentos_por_tipo'] = dict(cursor.fetchall())
                
            except psycopg2.ProgrammingError:
                # Tabela ainda não existe
                stats['total_documentos_pncp'] = 0
                stats['documentos_por_tipo'] = {}
            
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}
        finally:
            if conn:
                self.return_connection(conn)
    
    def verificar_saude_sistema(self) -> Dict[str, Any]:
        """
        Verifica a saúde do sistema de banco de dados.
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Testa conexão
            cursor.execute("SELECT 1")
            
            # Verifica extensões
            cursor.execute("""
                SELECT extname FROM pg_extension 
                WHERE extname IN ('vector', 'pg_trgm', 'unaccent')
            """)
            extensoes = [row[0] for row in cursor.fetchall()]
            
            # Verifica tabelas
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name IN ('contratacoes', 'contratacoes_embeddings', 'documentos_pncp')
            """)
            tabelas = [row[0] for row in cursor.fetchall()]
            
            return {
                'conexao_ok': True,
                'extensoes_instaladas': extensoes,
                'tabelas_existentes': tabelas,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro na verificação de saúde: {e}")
            return {
                'conexao_ok': False,
                'erro': str(e),
                'timestamp': datetime.now().isoformat()
            }
        finally:
            if conn:
                self.return_connection(conn)


# Instância global do gerenciador
supabase_manager = SupabaseManager()
