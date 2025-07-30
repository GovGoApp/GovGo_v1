#!/usr/bin/env python3
"""
GovGo V1 - Setup Principal
========================

Script de configuração e inicialização do sistema GovGo V1.
Este é o ponto de entrada principal para configurar e executar o sistema.
"""

import os
import sys
import argparse
from pathlib import Path

# Adiciona o diretório atual ao path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def setup_environment():
    """Configura o ambiente inicial do sistema."""
    print("🏛️ GovGo V1 - Setup do Sistema")
    print("=" * 50)
    
    # Verifica se .env existe
    env_file = current_dir / ".env"
    env_template = current_dir / ".env.template"
    
    if not env_file.exists():
        if env_template.exists():
            print("📋 Arquivo .env não encontrado. Copiando .env.template...")
            import shutil
            shutil.copy(env_template, env_file)
            print("✅ Arquivo .env criado.")
            print("⚠️  IMPORTANTE: Edite o arquivo .env com suas credenciais!")
            return False
        else:
            print("❌ Arquivo .env.template não encontrado!")
            return False
    
    print("✅ Arquivo .env encontrado.")
    return True

def setup_database():
    """Executa setup do banco de dados."""
    print("\n🗄️ Configurando banco de dados...")
    
    try:
        from scripts.setup_database import main as setup_db_main
        result = setup_db_main()
        if result == 0:
            print("✅ Banco de dados configurado com sucesso!")
            return True
        else:
            print("❌ Erro na configuração do banco de dados.")
            return False
    except Exception as e:
        print(f"❌ Erro ao executar setup do banco: {e}")
        return False

def run_tests():
    """Executa testes do sistema."""
    print("\n🧪 Executando testes...")
    
    try:
        from tests.test_setup import main as test_main
        result = test_main()
        if result == 0:
            print("✅ Todos os testes passaram!")
            return True
        else:
            print("❌ Alguns testes falharam.")
            return False
    except Exception as e:
        print(f"❌ Erro ao executar testes: {e}")
        return False

def run_examples():
    """Executa exemplos de uso."""
    print("\n📚 Executando exemplos...")
    
    try:
        from examples.examples import main as examples_main
        result = examples_main()
        if result == 0:
            print("✅ Exemplos executados com sucesso!")
            return True
        else:
            print("❌ Alguns exemplos falharam.")
            return False
    except Exception as e:
        print(f"❌ Erro ao executar exemplos: {e}")
        return False

def migrate_data():
    """Executa migração de dados do V0."""
    print("\n🔄 Migrando dados do V0...")
    
    try:
        from scripts.migrate_data import main as migrate_main
        result = migrate_main()
        if result == 0:
            print("✅ Migração concluída com sucesso!")
            return True
        else:
            print("❌ Erro na migração de dados.")
            return False
    except Exception as e:
        print(f"❌ Erro ao executar migração: {e}")
        return False

def check_status():
    """Verifica status do sistema."""
    print("\n📊 Verificando status do sistema...")
    
    try:
        from core.database import supabase_manager
        stats = supabase_manager.obter_estatisticas()
        saude = supabase_manager.verificar_saude_sistema()
        
        print(f"   Contratações: {stats.get('total_contratacoes', 0):,}")
        print(f"   Documentos V1: {stats.get('total_documentos_pncp', 0):,}")
        print(f"   Conexão: {'✅ OK' if saude.get('conexao_ok') else '❌ Falha'}")
        
        return saude.get('conexao_ok', False)
        
    except Exception as e:
        print(f"❌ Erro ao verificar status: {e}")
        return False

def main():
    """Função principal do setup."""
    parser = argparse.ArgumentParser(
        description="GovGo V1 - Setup e Gerenciamento do Sistema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Comandos disponíveis:
  setup     - Configuração inicial completa
  database  - Configurar apenas banco de dados
  test      - Executar testes do sistema
  examples  - Executar exemplos de uso
  migrate   - Migrar dados do V0 para V1
  status    - Verificar status do sistema
  
Exemplos:
  python setup.py setup      # Configuração completa
  python setup.py test       # Apenas testes
  python setup.py status     # Verificar status
        """
    )
    
    parser.add_argument(
        'command',
        choices=['setup', 'database', 'test', 'examples', 'migrate', 'status'],
        help='Comando a ser executado'
    )
    
    parser.add_argument(
        '--skip-env',
        action='store_true',
        help='Pular verificação do arquivo .env'
    )
    
    args = parser.parse_args()
    
    # Configuração inicial do ambiente
    if not args.skip_env and args.command != 'status':
        if not setup_environment():
            print("\n⚠️  Configure o arquivo .env antes de continuar.")
            return 1
    
    # Executa comando solicitado
    success = False
    
    if args.command == 'setup':
        print("\n🚀 Executando configuração completa...")
        env_ok = setup_environment()
        db_ok = setup_database() if env_ok else False
        test_ok = run_tests() if db_ok else False
        success = env_ok and db_ok and test_ok
        
    elif args.command == 'database':
        success = setup_database()
        
    elif args.command == 'test':
        success = run_tests()
        
    elif args.command == 'examples':
        success = run_examples()
        
    elif args.command == 'migrate':
        success = migrate_data()
        
    elif args.command == 'status':
        success = check_status()
    
    # Resultado final
    print("\n" + "=" * 50)
    if success:
        print("🎉 Comando executado com sucesso!")
        if args.command == 'setup':
            print("\n📋 Próximos passos:")
            print("   1. Edite o arquivo .env com suas credenciais")
            print("   2. Execute: python setup.py status")
            print("   3. Execute: python setup.py examples")
        return 0
    else:
        print("❌ Comando falhou. Verifique os erros acima.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
