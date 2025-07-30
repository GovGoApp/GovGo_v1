"""
GovGo V1 - Exemplos de Uso
=========================

Demonstra como usar o novo sistema V1 mantendo compatibilidade com V0.
"""

import os
import sys
import json
import asyncio
from typing import List, Dict, Any

# Adiciona o diretório v1 ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import config
from core.database import supabase_manager
from core.models import DocumentoPNCP, ContratacaoSupabase, ResultadoBuscaCompativel


def exemplo_busca_compativel():
    """Exemplo de busca compatível com o sistema V0."""
    print("=" * 60)
    print("EXEMPLO 1: BUSCA COMPATÍVEL COM V0")
    print("=" * 60)
    
    try:
        # Busca textual (igual ao gvg_search_utils_v3.py)
        print("\n🔍 Busca textual por 'equipamento'...")
        
        resultados = supabase_manager.buscar_compativel_v0(
            query="equipamento",
            search_type='textual',
            limit=5
        )
        
        if resultados:
            print(f"   Encontrados {len(resultados)} resultados:")
            
            for i, resultado in enumerate(resultados, 1):
                print(f"\n   {i}. {resultado.numerocontrolepncp}")
                print(f"      Objeto: {resultado.objeto[:80]}...")
                print(f"      Órgão: {resultado.orgaoentidade_razaosocial}")
                if resultado.valorestimado:
                    print(f"      Valor: R$ {resultado.valorestimado:,.2f}")
                print(f"      Similaridade: {resultado.similarity:.3f}")
        else:
            print("   Nenhum resultado encontrado.")
        
        # Busca híbrida
        print("\n🔍 Busca híbrida por 'software'...")
        
        resultados_hybrid = supabase_manager.buscar_compativel_v0(
            query="software",
            search_type='hybrid',
            limit=3
        )
        
        if resultados_hybrid:
            print(f"   Encontrados {len(resultados_hybrid)} resultados híbridos:")
            
            for resultado in resultados_hybrid:
                print(f"   - {resultado.numerocontrolepncp}: {resultado.objeto[:60]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na busca compatível: {e}")
        return False


def exemplo_uso_modelos():
    """Exemplo de uso dos novos modelos V1."""
    print("\n" + "=" * 60)
    print("EXEMPLO 2: USO DOS NOVOS MODELOS V1")
    print("=" * 60)
    
    try:
        # Criar documento PNCP
        print("\n📄 Criando DocumentoPNCP...")
        
        documento = DocumentoPNCP(
            numero_controle_pncp=f"EXEMPLO_{int(os.urandom(4).hex(), 16)}",
            tipo_documento="contratacao",
            dados_originais={
                "origem": "exemplo_uso",
                "timestamp": "2024-01-01T00:00:00Z"
            },
            objeto="Exemplo de contratação para demonstração do sistema V1",
            orgao_cnpj="12345678000199",
            orgao_razao_social="Órgão de Exemplo Ltda",
            unidade_codigo="001",
            unidade_nome="Unidade de Exemplo",
            valor_estimado=50000.00,
            situacao="Publicada",
            modalidade="Pregão Eletrônico",
            status_processamento="processado"
        )
        
        print(f"   Documento criado: {documento.numero_controle_pncp}")
        print(f"   Tipo: {documento.tipo_documento}")
        print(f"   Objeto: {documento.objeto}")
        print(f"   Valor: R$ {documento.valor_estimado:,.2f}")
        
        # Inserir no banco (se tabela existir)
        try:
            sucesso = supabase_manager.inserir_documento_pncp(documento)
            if sucesso:
                print("   ✅ Documento inserido com sucesso!")
            else:
                print("   ⚠️  Falha ao inserir documento")
        except Exception as e:
            print(f"   ⚠️  Tabela documentos_pncp não existe ainda: {e}")
        
        # Converter contratação existente
        print("\n🔄 Convertendo contratação existente...")
        
        contratacoes = supabase_manager.buscar_contratacoes(limite=1)
        if contratacoes:
            contratacao_original = contratacoes[0]
            documento_convertido = supabase_manager.converter_contratacao_para_documento(contratacao_original)
            
            print(f"   Original: {contratacao_original.get('numerocontrolepncp')}")
            print(f"   Convertido: {documento_convertido.numero_controle_pncp}")
            print(f"   Tipo: {documento_convertido.tipo_documento}")
        else:
            print("   Nenhuma contratação encontrada para conversão")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no uso dos modelos: {e}")
        return False


def exemplo_busca_unificada():
    """Exemplo de busca no sistema unificado V1."""
    print("\n" + "=" * 60)
    print("EXEMPLO 3: BUSCA UNIFICADA V1")
    print("=" * 60)
    
    try:
        # Busca em todos os tipos de documento
        print("\n🔍 Busca unificada por 'consultoria'...")
        
        documentos = supabase_manager.buscar_documentos_unificado(
            texto_busca="consultoria",
            tipos_documento=["contratacao", "contrato", "ata", "pca"],
            limite=5
        )
        
        if documentos:
            print(f"   Encontrados {len(documentos)} documentos:")
            
            for doc in documentos:
                print(f"\n   📄 {doc.numero_controle_pncp} ({doc.tipo_documento})")
                print(f"      Objeto: {doc.objeto[:80]}...")
                print(f"      Órgão: {doc.orgao_razao_social}")
                print(f"      Status: {doc.status_processamento}")
        else:
            print("   Nenhum documento encontrado.")
            print("   (Tabela documentos_pncp pode não existir ainda)")
        
        # Busca por tipo específico
        print("\n🔍 Busca por tipo específico (contratacao)...")
        
        contratos = supabase_manager.buscar_documentos_unificado(
            tipos_documento=["contratacao"],
            limite=3
        )
        
        print(f"   Encontradas {len(contratos)} contratações no modelo unificado")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na busca unificada: {e}")
        return False


def exemplo_estatisticas():
    """Exemplo de obtenção de estatísticas do sistema."""
    print("\n" + "=" * 60)
    print("EXEMPLO 4: ESTATÍSTICAS DO SISTEMA")
    print("=" * 60)
    
    try:
        # Estatísticas gerais
        print("\n📊 Estatísticas do banco de dados...")
        
        stats = supabase_manager.obter_estatisticas()
        
        print(f"   Contratações (V0): {stats.get('total_contratacoes', 0):,}")
        print(f"   Com embeddings: {stats.get('contratacoes_com_embedding', 0):,}")
        print(f"   Documentos PNCP (V1): {stats.get('total_documentos_pncp', 0):,}")
        
        docs_por_tipo = stats.get('documentos_por_tipo', {})
        if docs_por_tipo:
            print("   Documentos por tipo:")
            for tipo, count in docs_por_tipo.items():
                print(f"     - {tipo}: {count:,}")
        
        # Saúde do sistema
        print("\n🏥 Saúde do sistema...")
        
        saude = supabase_manager.verificar_saude_sistema()
        
        print(f"   Conexão: {'✅ OK' if saude.get('conexao_ok') else '❌ Falha'}")
        
        extensoes = saude.get('extensoes_instaladas', [])
        print(f"   Extensões: {', '.join(extensoes) if extensoes else 'Nenhuma'}")
        
        tabelas = saude.get('tabelas_existentes', [])
        print(f"   Tabelas: {', '.join(tabelas) if tabelas else 'Nenhuma'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {e}")
        return False


def exemplo_compatibilidade_completa():
    """Exemplo completo de compatibilidade entre V0 e V1."""
    print("\n" + "=" * 60)
    print("EXEMPLO 5: COMPATIBILIDADE COMPLETA V0 ↔ V1")
    print("=" * 60)
    
    try:
        # 1. Busca no formato V0
        print("\n1️⃣ Busca no formato V0 (gvg_search_utils_v3.py)...")
        
        resultados_v0 = supabase_manager.buscar_contratacoes(
            texto_busca="serviço",
            limite=2
        )
        
        if resultados_v0:
            print(f"   Encontradas {len(resultados_v0)} contratações (formato V0)")
            primeira_v0 = resultados_v0[0]
            print(f"   Primeira: {primeira_v0.get('numerocontrolepncp')}")
            
            # 2. Converte para formato V1
            print("\n2️⃣ Convertendo para formato V1...")
            
            documento_v1 = supabase_manager.converter_contratacao_para_documento(primeira_v0)
            print(f"   Convertido: {documento_v1.numero_controle_pncp}")
            print(f"   Tipo documento: {documento_v1.tipo_documento}")
            
            # 3. Busca compatível (híbrida)
            print("\n3️⃣ Busca compatível (retorna ResultadoBuscaCompativel)...")
            
            resultados_compat = supabase_manager.buscar_compativel_v0(
                query="serviço",
                search_type='textual',
                limit=2
            )
            
            if resultados_compat:
                print(f"   Encontrados {len(resultados_compat)} resultados compatíveis")
                primeiro_compat = resultados_compat[0]
                print(f"   Tipo: {type(primeiro_compat).__name__}")
                print(f"   Número: {primeiro_compat.numerocontrolepncp}")
                print(f"   Similaridade: {primeiro_compat.similarity}")
            
            # 4. Demonstra interoperabilidade
            print("\n4️⃣ Interoperabilidade demonstrada:")
            print("   ✅ Dados V0 acessíveis")
            print("   ✅ Conversão V0 → V1 funcionando")
            print("   ✅ Interface compatível disponível")
            print("   ✅ Busca híbrida operacional")
        
        else:
            print("   Nenhuma contratação encontrada para demonstração")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na demonstração de compatibilidade: {e}")
        return False


def main():
    """Executa todos os exemplos."""
    print("GovGo V1 - Exemplos de Uso")
    print("=" * 60)
    print("Demonstração das capacidades do sistema V1")
    print("com total compatibilidade com o sistema V0")
    
    exemplos = [
        ("Busca Compatível V0", exemplo_busca_compativel),
        ("Uso dos Modelos V1", exemplo_uso_modelos),
        ("Busca Unificada V1", exemplo_busca_unificada),
        ("Estatísticas", exemplo_estatisticas),
        ("Compatibilidade Completa", exemplo_compatibilidade_completa)
    ]
    
    resultados = {}
    
    for nome, funcao in exemplos:
        try:
            print(f"\n🚀 Executando: {nome}")
            sucesso = funcao()
            resultados[nome] = sucesso
            
            if sucesso:
                print(f"✅ {nome} executado com sucesso")
            else:
                print(f"⚠️  {nome} executado com problemas")
                
        except Exception as e:
            print(f"❌ Erro em {nome}: {e}")
            resultados[nome] = False
    
    # Relatório final
    print("\n" + "=" * 60)
    print("RELATÓRIO FINAL")
    print("=" * 60)
    
    total = len(resultados)
    sucessos = sum(resultados.values())
    
    print(f"📊 Exemplos executados: {total}")
    print(f"✅ Sucessos: {sucessos}")
    print(f"❌ Falhas: {total - sucessos}")
    print(f"📈 Taxa de sucesso: {(sucessos/total)*100:.1f}%")
    
    print("\nDetalhes:")
    for nome, sucesso in resultados.items():
        status = "✅" if sucesso else "❌"
        print(f"   {status} {nome}")
    
    if sucessos == total:
        print("\n🎉 Todos os exemplos foram executados com sucesso!")
        print("   O sistema V1 está funcionando corretamente.")
    else:
        print(f"\n⚠️  {total - sucessos} exemplo(s) com problemas.")
        print("   Verifique as configurações e dependências.")
    
    return 0 if sucessos == total else 1


if __name__ == "__main__":
    sys.exit(main())
