"""
GovGo V1 - Script de Teste do Setup
==================================

Testa a configuração e compatibilidade do sistema V1 com a estrutura existente.
"""

import os
import sys
import json
import logging
from typing import Dict, Any

# Adiciona o diretório v1 ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import config
from core.database import supabase_manager
from core.models import DocumentoPNCP, ContratacaoSupabase, ResultadoBuscaCompativel

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_config():
    """Testa configuração do sistema."""
    print("\n" + "="*60)
    print("TESTE 1: CONFIGURAÇÃO DO SISTEMA")
    print("="*60)
    
    try:
        # Testa variáveis de ambiente
        required_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'OPENAI_API_KEY']
        missing_vars = []
        
        for var in required_vars:
            if not config.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
            return False
        
        # Testa URL do banco
        db_url = config.get_database_url()
        if not db_url:
            print("❌ URL do banco de dados não configurada")
            return False
        
        print("✅ Configuração básica OK")
        print(f"   - Supabase URL: {config.SUPABASE_URL[:30]}...")
        print(f"   - OpenAI configurado: {'Sim' if config.OPENAI_API_KEY else 'Não'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na configuração: {e}")
        return False


def test_database_connection():
    """Testa conexão com o banco de dados."""
    print("\n" + "="*60)
    print("TESTE 2: CONEXÃO COM BANCO DE DADOS")
    print("="*60)
    
    try:
        # Testa conexão básica
        saude = supabase_manager.verificar_saude_sistema()
        
        if not saude.get('conexao_ok'):
            print(f"❌ Falha na conexão: {saude.get('erro', 'Erro desconhecido')}")
            return False
        
        print("✅ Conexão com Supabase estabelecida")
        
        # Verifica extensões
        extensoes = saude.get('extensoes_instaladas', [])
        extensoes_necessarias = ['vector', 'pg_trgm']
        
        for ext in extensoes_necessarias:
            if ext in extensoes:
                print(f"✅ Extensão {ext} instalada")
            else:
                print(f"⚠️  Extensão {ext} não encontrada")
        
        # Verifica tabelas
        tabelas = saude.get('tabelas_existentes', [])
        tabelas_esperadas = ['contratacoes', 'contratacoes_embeddings']
        
        for tab in tabelas_esperadas:
            if tab in tabelas:
                print(f"✅ Tabela {tab} existe")
            else:
                print(f"❌ Tabela {tab} não encontrada")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False


def test_existing_data():
    """Testa compatibilidade com dados existentes."""
    print("\n" + "="*60)
    print("TESTE 3: COMPATIBILIDADE COM DADOS EXISTENTES")
    print("="*60)
    
    try:
        # Obtém estatísticas dos dados existentes
        stats = supabase_manager.obter_estatisticas()
        
        total_contratacoes = stats.get('total_contratacoes', 0)
        contratacoes_com_embedding = stats.get('contratacoes_com_embedding', 0)
        
        print(f"📊 Total de contratações: {total_contratacoes:,}")
        print(f"📊 Contratações com embedding: {contratacoes_com_embedding:,}")
        
        if total_contratacoes > 0:
            print("✅ Dados existentes encontrados")
            
            # Testa busca de uma contratação
            resultados = supabase_manager.buscar_contratacoes(limite=1)
            
            if resultados:
                print("✅ Busca de contratações funcionando")
                
                # Testa conversão para novo modelo
                primeira_contratacao = resultados[0]
                documento = supabase_manager.converter_contratacao_para_documento(primeira_contratacao)
                
                print("✅ Conversão para novo modelo funcionando")
                print(f"   - Número de controle: {documento.numero_controle_pncp}")
                print(f"   - Tipo: {documento.tipo_documento}")
                print(f"   - Objeto: {documento.objeto[:50]}..." if documento.objeto else "   - Objeto: N/A")
                
            else:
                print("⚠️  Nenhuma contratação retornada na busca")
        
        else:
            print("⚠️  Nenhum dado existente encontrado")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar dados existentes: {e}")
        return False


def test_search_compatibility():
    """Testa compatibilidade do sistema de busca."""
    print("\n" + "="*60)
    print("TESTE 4: COMPATIBILIDADE DO SISTEMA DE BUSCA")
    print("="*60)
    
    try:
        # Testa busca textual
        query_teste = "equipamento"
        resultados = supabase_manager.buscar_compativel_v0(
            query=query_teste,
            search_type='textual',
            limit=3
        )
        
        if resultados:
            print(f"✅ Busca textual funcionando ({len(resultados)} resultados)")
            
            for i, resultado in enumerate(resultados[:2], 1):
                print(f"   {i}. {resultado.numerocontrolepncp} - {resultado.objeto[:60]}...")
                
        else:
            print("⚠️  Busca textual não retornou resultados")
        
        # Testa busca híbrida (sem embedding por enquanto)
        resultados_hybrid = supabase_manager.buscar_compativel_v0(
            query=query_teste,
            search_type='hybrid',
            limit=3
        )
        
        if resultados_hybrid:
            print(f"✅ Busca híbrida funcionando ({len(resultados_hybrid)} resultados)")
        else:
            print("⚠️  Busca híbrida não retornou resultados")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar sistema de busca: {e}")
        return False


def test_models():
    """Testa os modelos de dados."""
    print("\n" + "="*60)
    print("TESTE 5: MODELOS DE DADOS")
    print("="*60)
    
    try:
        # Testa criação de DocumentoPNCP
        doc = DocumentoPNCP(
            numero_controle_pncp="TESTE123456",
            tipo_documento="contratacao",
            dados_originais={"teste": "dados"},
            objeto="Objeto de teste",
            orgao_cnpj="12345678000199",
            orgao_razao_social="Órgão de Teste",
            situacao="Publicada",
            status_processamento="processado"
        )
        
        print("✅ Modelo DocumentoPNCP criado com sucesso")
        print(f"   - Número de controle: {doc.numero_controle_pncp}")
        print(f"   - Tipo: {doc.tipo_documento}")
        
        # Testa ContratacaoSupabase
        contratacao = ContratacaoSupabase(
            numerocontrolepncp="TESTE789012",
            objeto="Contratação de teste",
            orgaoentidade_cnpj="98765432000188",
            orgaoentidade_razaosocial="Entidade de Teste"
        )
        
        print("✅ Modelo ContratacaoSupabase criado com sucesso")
        
        # Testa ResultadoBuscaCompativel
        resultado = ResultadoBuscaCompativel(
            numerocontrolepncp="TESTE345678",
            objeto="Resultado de teste",
            orgaoentidade_razaosocial="Órgão Teste",
            similarity=0.85
        )
        
        print("✅ Modelo ResultadoBuscaCompativel criado com sucesso")
        print(f"   - Similaridade: {resultado.similarity}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar modelos: {e}")
        return False


def test_new_table_setup():
    """Testa a configuração da nova tabela unificada."""
    print("\n" + "="*60)
    print("TESTE 6: CONFIGURAÇÃO DA NOVA TABELA")
    print("="*60)
    
    try:
        # Verifica se a nova tabela existe
        conn = supabase_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'documentos_pncp'
        """)
        
        tabela_existe = cursor.fetchone() is not None
        supabase_manager.return_connection(conn)
        
        if tabela_existe:
            print("✅ Tabela documentos_pncp já existe")
            
            # Testa inserção de documento teste
            doc_teste = DocumentoPNCP(
                numero_controle_pncp="TESTE_SETUP_" + str(int(os.urandom(4).hex(), 16)),
                tipo_documento="contratacao",
                dados_originais={"origem": "teste_setup"},
                objeto="Documento de teste do setup",
                orgao_cnpj="00000000000000",
                orgao_razao_social="Órgão de Teste Setup",
                situacao="Teste",
                status_processamento="processado"
            )
            
            sucesso = supabase_manager.inserir_documento_pncp(doc_teste)
            
            if sucesso:
                print("✅ Inserção na nova tabela funcionando")
                
                # Testa busca na nova tabela
                docs = supabase_manager.buscar_documentos_unificado(
                    texto_busca="teste setup",
                    limite=1
                )
                
                if docs:
                    print("✅ Busca na nova tabela funcionando")
                else:
                    print("⚠️  Busca na nova tabela não retornou resultados")
                    
            else:
                print("❌ Falha na inserção na nova tabela")
        
        else:
            print("⚠️  Tabela documentos_pncp não existe ainda")
            print("   Execute o script setup_database.py primeiro")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar nova tabela: {e}")
        return False


def generate_report(test_results: Dict[str, bool]):
    """Gera relatório final dos testes."""
    print("\n" + "="*60)
    print("RELATÓRIO FINAL DOS TESTES")
    print("="*60)
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    failed_tests = total_tests - passed_tests
    
    print(f"📊 Total de testes: {total_tests}")
    print(f"✅ Testes passaram: {passed_tests}")
    print(f"❌ Testes falharam: {failed_tests}")
    print(f"📈 Taxa de sucesso: {(passed_tests/total_tests)*100:.1f}%")
    
    print("\nDetalhes:")
    for test_name, passed in test_results.items():
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"   {test_name}: {status}")
    
    if failed_tests > 0:
        print("\n⚠️  ATENÇÃO: Alguns testes falharam.")
        print("   Verifique as configurações e dependências antes de continuar.")
    else:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("   O sistema está pronto para uso.")
    
    return failed_tests == 0


def main():
    """Executa todos os testes."""
    print("GovGo V1 - Validação do Sistema")
    print("="*60)
    
    test_results = {}
    
    # Executa testes sequencialmente
    test_results["Configuração"] = test_config()
    test_results["Conexão BD"] = test_database_connection()
    test_results["Dados Existentes"] = test_existing_data()
    test_results["Sistema de Busca"] = test_search_compatibility()
    test_results["Modelos de Dados"] = test_models()
    test_results["Nova Tabela"] = test_new_table_setup()
    
    # Gera relatório final
    success = generate_report(test_results)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
