#!/usr/bin/env python3
"""
govgo_search_terminal_v1.py
Sistema de Busca PNCP V1 - Terminal Interativo Completo
=======================================================

🚀 MIGRAÇÃO COMPLETA V0 → V1:
• Baseado no GvG_SP_Search_Terminal_v9.py 
• Sistema unificado de busca para GovGo V1
• Nova base Supabase V1: hemztmtbejcbhgfmsvfq
• Interface Rich modernizada e modular
• Código organizado em 4 partes modulares

🎯 FUNCIONALIDADES PRINCIPAIS V1:
• Interface interativa Rich com menus coloridos
• Busca semântica, palavras-chave e híbrida com IA
• Sistema de relevância 3 níveis configurável
• Processamento inteligente de consultas V1
• Análise e sumarização de documentos
• Exportação automática JSON/PDF/Excel/LOG
• Histórico de buscas e estatísticas da sessão
• Configurações dinâmicas e personalizáveis

📋 ESTRUTURA MODULAR V1:
• PARTE 1: Configurações, imports, classes básicas
• PARTE 2: Funções de menu e interface Rich
• PARTE 3: Funções de busca e processamento  
• PARTE 4: Função principal e controles de sistema

🔧 REQUISITOS V1:
• Python 3.8+
• Rich library para interface
• Sistema V1 configurado (govgo_search_engine_v1.py)
• Processador V1 (govgo_document_processor_v1.py)
• Banco PostgreSQL com pgvector (Supabase V1)
• OpenAI API key para processamento inteligente

📚 EXEMPLOS DE USO:
    # Executar terminal interativo
    python govgo_search_terminal_v1.py
    
    # Executar com configurações específicas  
    python govgo_search_terminal_v1.py --config custom_config.json
    
    # Modo debug
    python govgo_search_terminal_v1.py --debug

⚙️ CONFIGURAÇÕES PADRÃO V1:
• Tipo de Busca: Semântica
• Abordagem: Filtro Categórico  
• Relevância: Nível 1 (Sem filtro)
• Ordenação: Por Valor Estimado
• Max Resultados: 30
• TOP Categorias: 10
• Filtrar Encerradas: Ativo
• Negation Embeddings: Ativo
• Export Automático: Ativo

🚨 MIGRAÇÃO V0 → V1:
• Tabelas: categorias → categoria, contratacoes → contratacao
• Campos: snake_case (orgao_entidade_razao_social, etc.)
• Embeddings: embedding_vector → embeddings
• Engine: Novo motor unificado V1
• Interface: Rich UI modernizada
• Funcionalidades: Processamento inteligente V1
"""

import os
import sys
import argparse
import json
from pathlib import Path

# Verificar se todas as partes estão disponíveis
def check_parts_available():
    """Verifica se todas as partes modulares estão disponíveis"""
    current_dir = Path(__file__).parent
    parts = [
        'govgo_search_terminal_v1_part1.py',
        'govgo_search_terminal_v1_part2.py', 
        'govgo_search_terminal_v1_part3.py',
        'govgo_search_terminal_v1_part4.py'
    ]
    
    missing_parts = []
    for part in parts:
        if not (current_dir / part).exists():
            missing_parts.append(part)
    
    if missing_parts:
        print("❌ ERRO: Partes modulares não encontradas:")
        for part in missing_parts:
            print(f"   • {part}")
        print("\n💡 Certifique-se que todas as 4 partes estão na mesma pasta!")
        return False
    
    return True

def load_config_from_file(config_path: str):
    """Carrega configuração de arquivo JSON"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Erro ao carregar configuração: {e}")
        return None

def setup_argument_parser():
    """Configura parser de argumentos V1"""
    parser = argparse.ArgumentParser(
        description='Sistema de Busca PNCP V1 - Terminal Interativo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--config', '-c',
        help='Arquivo JSON com configurações personalizadas',
        type=str,
        metavar='FILE'
    )
    
    parser.add_argument(
        '--debug', '-d',
        help='Ativar modo debug com informações detalhadas',
        action='store_true'
    )
    
    parser.add_argument(
        '--version', '-v',
        help='Mostrar versão e informações do sistema',
        action='store_true'
    )
    
    parser.add_argument(
        '--check-deps', '--check',
        help='Verificar dependências e componentes V1',
        action='store_true'
    )
    
    return parser

def show_version_info():
    """Mostra informações de versão V1"""
    print("🚀 GovGo Search Terminal V1")
    print("=" * 50)
    print(f"Versão: 1.0.0")
    print(f"Data: Dezembro 2024") 
    print(f"Base: Supabase V1 (hemztmtbejcbhgfmsvfq)")
    print(f"Engine: govgo_search_engine_v1.py")
    print(f"Processador: govgo_document_processor_v1.py")
    print(f"Interface: Rich Terminal UI")
    print(f"Python: {sys.version}")
    print("=" * 50)

def check_dependencies():
    """Verifica dependências e componentes V1"""
    print("🔍 Verificando Componentes V1...")
    print("=" * 50)
    
    # Verificar partes modulares
    if check_parts_available():
        print("✅ Partes modulares: OK")
    else:
        print("❌ Partes modulares: FALHA")
        return False
    
    # Verificar Rich
    try:
        import rich
        print(f"✅ Rich UI: {rich.__version__}")
    except ImportError:
        print("❌ Rich UI: NÃO INSTALADO")
        print("   pip install rich")
        return False
    
    # Verificar motor de busca V1
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from govgo_search_engine_v1 import GovGoSearchEngine
        print("✅ Motor de Busca V1: OK")
    except ImportError as e:
        print(f"❌ Motor de Busca V1: FALHA - {e}")
        return False
    
    # Verificar processador de documentos V1
    try:
        from govgo_document_processor_v1 import get_query_processor
        print("✅ Processador de Documentos V1: OK") 
    except ImportError:
        print("⚠️ Processador de Documentos V1: INDISPONÍVEL")
        print("   (Funcionalidade opcional)")
    
    # Verificar pandas/numpy
    try:
        import pandas as pd
        import numpy as np
        print(f"✅ Pandas/NumPy: {pd.__version__}/{np.__version__}")
    except ImportError:
        print("❌ Pandas/NumPy: NÃO INSTALADO")
        print("   pip install pandas numpy")
        return False
    
    # Verificar dotenv
    try:
        from dotenv import load_dotenv
        print("✅ Python-dotenv: OK")
    except ImportError:
        print("❌ Python-dotenv: NÃO INSTALADO")
        print("   pip install python-dotenv")
        return False
    
    print("=" * 50)
    print("✅ Verificação de dependências concluída!")
    return True

def main():
    """Função principal do arquivo unificado V1"""
    # Parser de argumentos
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Comandos especiais
    if args.version:
        show_version_info()
        return
    
    if args.check_deps:
        if check_dependencies():
            print("\n🚀 Sistema pronto para uso!")
        else:
            print("\n❌ Corrija as dependências antes de continuar")
        return
    
    # Verificar partes modulares
    if not check_parts_available():
        sys.exit(1)
    
    # Debug mode
    if args.debug:
        print("🐛 Modo DEBUG ativado")
        os.environ['GOVGO_DEBUG'] = '1'
    
    try:
        # Importar e executar função principal
        from govgo_search_terminal_v1_part4 import main as terminal_main
        
        # Carregar configuração personalizada se fornecida
        if args.config:
            config_data = load_config_from_file(args.config)
            if config_data:
                print(f"✅ Configuração carregada: {args.config}")
                # TODO: Aplicar configuração personalizada ao TerminalState
            else:
                print("⚠️ Usando configuração padrão")
        
        # Executar terminal principal V1
        terminal_main()
        
    except ImportError as e:
        print(f"❌ ERRO: Falha ao importar componentes V1: {e}")
        print("💡 Execute --check-deps para diagnosticar o problema")
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n👋 Terminal V1 encerrado pelo usuário")
    
    except Exception as e:
        print(f"❌ ERRO INESPERADO: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
