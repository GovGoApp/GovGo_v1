#!/usr/bin/env python3

print("=== TESTE 05F DEBUG ===")

# Teste básico de importações
try:
    print("Importando módulos...")
    import os
    import sys
    import argparse
    print("✓ Módulos básicos OK")
    
    from dotenv import load_dotenv
    print("✓ dotenv OK")
    
    from rich.console import Console
    print("✓ rich OK")
    
    import psycopg2
    print("✓ psycopg2 OK")
    
except Exception as e:
    print(f"❌ Erro na importação: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Teste carregar .env
try:
    print("\nCarregando .env...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, ".env")
    print(f"Procurando .env em: {env_path}")
    
    load_dotenv(env_path)
    print("✓ .env carregado")
    
    # Teste variáveis
    host = os.getenv('SUPABASE_HOST')
    user = os.getenv('SUPABASE_USER')
    print(f"Host: {'✓ OK' if host else '❌ VAZIO'}")
    print(f"User: {'✓ OK' if user else '❌ VAZIO'}")
    
except Exception as e:
    print(f"❌ Erro ao carregar .env: {e}")
    import traceback
    traceback.print_exc()

# Teste argumentos
try:
    print("\nTestando argumentos...")
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    
    print(f"Test mode: {args.test}")
    print(f"Debug mode: {args.debug}")
    print("✓ Argumentos OK")
    
except Exception as e:
    print(f"❌ Erro nos argumentos: {e}")
    import traceback
    traceback.print_exc()

print("\n=== TESTE CONCLUÍDO ===")
