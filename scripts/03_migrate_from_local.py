"""
GovGo V1 - Script de Migração de Dados
======================================

Migra dados da estrutura v0 para v1, mantendo compatibilidade total.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime
import time

# Adiciona o diretório v1 ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import config
from core.database import supabase_manager
from core.models import DocumentoPNCP

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationManager:
    """Gerenciador de migração de dados do v0 para v1."""
    
    def __init__(self):
        self.stats = {
            'total_processados': 0,
            'sucessos': 0,
            'falhas': 0,
            'duplicados': 0,
            'inicio': None,
            'fim': None
        }
    
    def verificar_prerequisites(self) -> bool:
        """Verifica se os pré-requisitos estão atendidos."""
        print("🔍 Verificando pré-requisitos...")
        
        try:
            # Verifica conexão
            saude = supabase_manager.verificar_saude_sistema()
            if not saude.get('conexao_ok'):
                print("❌ Conexão com banco não estabelecida")
                return False
            
            # Verifica se tabelas existem
            tabelas = saude.get('tabelas_existentes', [])
            
            if 'contratacoes' not in tabelas:
                print("❌ Tabela 'contratacoes' não encontrada")
                return False
            
            if 'documentos_pncp' not in tabelas:
                print("⚠️  Tabela 'documentos_pncp' não existe")
                print("   Execute primeiro: python setup_database.py")
                return False
            
            # Verifica dados existentes
            stats = supabase_manager.obter_estatisticas()
            total_contratacoes = stats.get('total_contratacoes', 0)
            
            if total_contratacoes == 0:
                print("⚠️  Nenhuma contratação encontrada para migrar")
                return False
            
            print(f"✅ {total_contratacoes:,} contratações encontradas para migração")
            return True
            
        except Exception as e:
            print(f"❌ Erro na verificação: {e}")
            return False
    
    def analisar_dados_existentes(self) -> Dict[str, Any]:
        """Analisa os dados existentes antes da migração."""
        print("\n📊 Analisando dados existentes...")
        
        try:
            conn = supabase_manager.get_connection()
            cursor = conn.cursor()
            
            # Contagem total
            cursor.execute("SELECT COUNT(*) FROM contratacoes")
            total = cursor.fetchone()[0]
            
            # Contratações por situação
            cursor.execute("""
                SELECT situacao, COUNT(*) 
                FROM contratacoes 
                GROUP BY situacao 
                ORDER BY COUNT(*) DESC
            """)
            por_situacao = dict(cursor.fetchall())
            
            # Contratações por órgão (top 10)
            cursor.execute("""
                SELECT orgaoentidade_razaosocial, COUNT(*) 
                FROM contratacoes 
                GROUP BY orgaoentidade_razaosocial 
                ORDER BY COUNT(*) DESC 
                LIMIT 10
            """)
            por_orgao = dict(cursor.fetchall())
            
            # Verifica campos obrigatórios
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN numerocontrolepncp IS NULL THEN 1 ELSE 0 END) as sem_numero,
                    SUM(CASE WHEN objeto IS NULL OR objeto = '' THEN 1 ELSE 0 END) as sem_objeto,
                    SUM(CASE WHEN orgaoentidade_cnpj IS NULL THEN 1 ELSE 0 END) as sem_cnpj
                FROM contratacoes
            """)
            problemas = cursor.fetchone()
            
            supabase_manager.return_connection(conn)
            
            analise = {
                'total': total,
                'por_situacao': por_situacao,
                'por_orgao': por_orgao,
                'problemas': {
                    'sem_numero_controle': problemas[0],
                    'sem_objeto': problemas[1],
                    'sem_cnpj': problemas[2]
                }
            }
            
            print(f"   Total: {total:,} contratações")
            print(f"   Situações: {len(por_situacao)} diferentes")
            print(f"   Órgãos: {len(por_orgao)} diferentes (top 10)")
            
            if problemas[0] > 0:
                print(f"   ⚠️  {problemas[0]} sem número de controle")
            if problemas[1] > 0:
                print(f"   ⚠️  {problemas[1]} sem objeto")
            if problemas[2] > 0:
                print(f"   ⚠️  {problemas[2]} sem CNPJ")
            
            return analise
            
        except Exception as e:
            print(f"❌ Erro na análise: {e}")
            return {}
    
    def migrar_contratacoes(self, batch_size: int = 1000, max_batches: int = None) -> bool:
        """Migra contratações em lotes."""
        print(f"\n🔄 Iniciando migração (lotes de {batch_size})...")
        
        self.stats['inicio'] = datetime.now()
        
        try:
            conn = supabase_manager.get_connection()
            cursor = conn.cursor()
            
            # Conta total para progresso
            cursor.execute("SELECT COUNT(*) FROM contratacoes")
            total_registros = cursor.fetchone()[0]
            
            print(f"   Total a migrar: {total_registros:,} registros")
            
            offset = 0
            batch_num = 0
            
            while True:
                batch_num += 1
                
                if max_batches and batch_num > max_batches:
                    print(f"   Limite de {max_batches} lotes atingido")
                    break
                
                # Busca lote
                cursor.execute("""
                    SELECT * FROM contratacoes 
                    ORDER BY created_at 
                    LIMIT %s OFFSET %s
                """, (batch_size, offset))
                
                batch = cursor.fetchall()
                
                if not batch:
                    break
                
                # Processa lote
                print(f"   Processando lote {batch_num} ({len(batch)} registros)...")
                
                sucessos_lote, falhas_lote = self._processar_lote(batch)
                
                self.stats['sucessos'] += sucessos_lote
                self.stats['falhas'] += falhas_lote
                self.stats['total_processados'] += len(batch)
                
                # Progresso
                progresso = (self.stats['total_processados'] / total_registros) * 100
                print(f"   Progresso: {progresso:.1f}% ({self.stats['total_processados']:,}/{total_registros:,})")
                
                offset += batch_size
                
                # Pequena pausa para não sobrecarregar
                time.sleep(0.1)
            
            supabase_manager.return_connection(conn)
            
            self.stats['fim'] = datetime.now()
            
            print(f"\n✅ Migração concluída!")
            self._imprimir_estatisticas()
            
            return self.stats['falhas'] == 0
            
        except Exception as e:
            print(f"❌ Erro na migração: {e}")
            self.stats['fim'] = datetime.now()
            return False
    
    def _processar_lote(self, batch: List[Tuple]) -> Tuple[int, int]:
        """Processa um lote de registros."""
        sucessos = 0
        falhas = 0
        
        for row in batch:
            try:
                # Converte tupla para dict
                # Assumindo ordem das colunas da tabela contratacoes
                dados = {
                    'numerocontrolepncp': row[1],  # Ajustar índices conforme schema
                    'objeto': row[2],
                    'orgaoentidade_cnpj': row[3],
                    'orgaoentidade_razaosocial': row[4],
                    'unidadeorcamentaria_codigo': row[5],
                    'unidadeorcamentaria_nome': row[6],
                    'valorestimado': row[7],
                    'situacao': row[8],
                    'modcompra': row[9],
                    'tipoprocedimento': row[10],
                    'justificativacontratacaodireta': row[11],
                    'created_at': row[12] if len(row) > 12 else None
                }
                
                # Converte para DocumentoPNCP
                documento = supabase_manager.converter_contratacao_para_documento(dados)
                
                # Insere no novo modelo
                if supabase_manager.inserir_documento_pncp(documento):
                    sucessos += 1
                else:
                    falhas += 1
                    
            except Exception as e:
                logger.error(f"Erro ao processar registro: {e}")
                falhas += 1
        
        return sucessos, falhas
    
    def verificar_integridade_migracao(self) -> Dict[str, Any]:
        """Verifica a integridade dos dados migrados."""
        print("\n🔍 Verificando integridade da migração...")
        
        try:
            conn = supabase_manager.get_connection()
            cursor = conn.cursor()
            
            # Conta registros originais
            cursor.execute("SELECT COUNT(*) FROM contratacoes")
            total_original = cursor.fetchone()[0]
            
            # Conta registros migrados
            cursor.execute("SELECT COUNT(*) FROM documentos_pncp WHERE tipo_documento = 'contratacao'")
            total_migrado = cursor.fetchone()[0]
            
            # Verifica alguns registros aleatórios
            cursor.execute("""
                SELECT c.numerocontrolepncp, c.objeto, c.orgaoentidade_razaosocial
                FROM contratacoes c
                ORDER BY RANDOM()
                LIMIT 5
            """)
            amostras = cursor.fetchall()
            
            verificacoes = []
            for amostra in amostras:
                numero_controle = amostra[0]
                
                cursor.execute("""
                    SELECT numero_controle_pncp, objeto, orgao_razao_social
                    FROM documentos_pncp 
                    WHERE numero_controle_pncp = %s AND tipo_documento = 'contratacao'
                """, (numero_controle,))
                
                migrado = cursor.fetchone()
                
                verificacoes.append({
                    'numero_controle': numero_controle,
                    'encontrado': migrado is not None,
                    'dados_batem': migrado == amostra if migrado else False
                })
            
            supabase_manager.return_connection(conn)
            
            # Resultados
            verificacoes_ok = sum(1 for v in verificacoes if v['encontrado'])
            
            print(f"   Registros originais: {total_original:,}")
            print(f"   Registros migrados: {total_migrado:,}")
            print(f"   Diferença: {abs(total_original - total_migrado):,}")
            print(f"   Verificações OK: {verificacoes_ok}/{len(verificacoes)}")
            
            if total_original == total_migrado and verificacoes_ok == len(verificacoes):
                print("✅ Integridade verificada com sucesso!")
                return {'ok': True, 'detalhes': {
                    'total_original': total_original,
                    'total_migrado': total_migrado,
                    'verificacoes_ok': verificacoes_ok
                }}
            else:
                print("⚠️  Possíveis problemas de integridade detectados")
                return {'ok': False, 'detalhes': {
                    'total_original': total_original,
                    'total_migrado': total_migrado,
                    'verificacoes_ok': verificacoes_ok
                }}
            
        except Exception as e:
            print(f"❌ Erro na verificação: {e}")
            return {'ok': False, 'erro': str(e)}
    
    def _imprimir_estatisticas(self):
        """Imprime estatísticas da migração."""
        duracao = self.stats['fim'] - self.stats['inicio']
        
        print(f"\n📊 Estatísticas da Migração:")
        print(f"   Duração: {duracao}")
        print(f"   Total processados: {self.stats['total_processados']:,}")
        print(f"   Sucessos: {self.stats['sucessos']:,}")
        print(f"   Falhas: {self.stats['falhas']:,}")
        print(f"   Duplicados: {self.stats['duplicados']:,}")
        
        if self.stats['total_processados'] > 0:
            taxa_sucesso = (self.stats['sucessos'] / self.stats['total_processados']) * 100
            print(f"   Taxa de sucesso: {taxa_sucesso:.1f}%")
            
            if duracao.total_seconds() > 0:
                registros_por_segundo = self.stats['total_processados'] / duracao.total_seconds()
                print(f"   Velocidade: {registros_por_segundo:.1f} registros/segundo")


def main():
    """Função principal do script de migração."""
    print("GovGo V1 - Migração de Dados")
    print("="*50)
    
    migration = MigrationManager()
    
    # Verificar pré-requisitos
    if not migration.verificar_prerequisites():
        print("\n❌ Pré-requisitos não atendidos. Abortando migração.")
        return 1
    
    # Analisar dados existentes
    analise = migration.analisar_dados_existentes()
    if not analise:
        print("\n❌ Falha na análise dos dados. Abortando migração.")
        return 1
    
    # Confirmar migração
    print(f"\n🤔 Deseja prosseguir com a migração de {analise['total']:,} registros?")
    resposta = input("   Digite 'sim' para continuar: ").lower().strip()
    
    if resposta != 'sim':
        print("Migração cancelada pelo usuário.")
        return 0
    
    # Executar migração
    sucesso = migration.migrar_contratacoes(
        batch_size=1000,
        max_batches=None  # None = migra tudo
    )
    
    if sucesso:
        # Verificar integridade
        integridade = migration.verificar_integridade_migracao()
        
        if integridade.get('ok'):
            print("\n🎉 Migração concluída com sucesso!")
            return 0
        else:
            print("\n⚠️  Migração concluída com possíveis problemas.")
            return 1
    else:
        print("\n❌ Migração falhou.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
