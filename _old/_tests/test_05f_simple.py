#!/usr/bin/env python3

print("=== TESTE 05F ULTRA SIMPLES ===")

try:
    print("Importando argparse...")
    import argparse
    
    print("Criando parser...")
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true')
    
    print("Fazendo parse...")
    args = parser.parse_args()
    
    print(f"Test mode: {args.test}")
    
    if args.test:
        print("MODO TESTE DETECTADO!")
    else:
        print("MODO NORMAL")
        
    print("Script finalizado com sucesso!")
        
except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()
