#!/usr/bin/env python3
"""
Utilitário para gerenciar e limpar recursos OpenAI
"""

import os
import sys
from pathlib import Path

# Importar OpenAI
try:
    from openai import OpenAI
except ImportError:
    print("❌ Erro: Biblioteca OpenAI não instalada")
    print("💡 Execute: pip install openai")
    sys.exit(1)

def load_openai_client():
    """Carrega cliente OpenAI"""
    try:
        env_path = Path(__file__).parent / "openai.env"
        
        if not env_path.exists():
            raise FileNotFoundError("Arquivo openai.env não encontrado")
        
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('api_key='):
                    api_key = line.split('=', 1)[1].strip()
                    break
            else:
                raise ValueError("api_key não encontrada no arquivo .env")
        
        return OpenAI(api_key=api_key)
        
    except Exception as e:
        print(f"❌ Erro ao carregar OpenAI: {e}")
        sys.exit(1)

def list_files(client):
    """Lista arquivos no OpenAI"""
    print("📁 ARQUIVOS NO OPENAI:")
    print("=" * 50)
    
    try:
        files = client.files.list()
        
        if not files.data:
            print("📭 Nenhum arquivo encontrado")
            return
        
        for file in files.data:
            size_mb = file.bytes / 1024 / 1024 if file.bytes else 0
            print(f"📄 {file.filename}")
            print(f"   ID: {file.id}")
            print(f"   Tamanho: {size_mb:.2f} MB")
            print(f"   Criado: {file.created_at}")
            print(f"   Propósito: {file.purpose}")
            print()
            
    except Exception as e:
        print(f"❌ Erro ao listar arquivos: {e}")

def cleanup_files(client):
    """Remove todos os arquivos"""
    print("🗑️ LIMPANDO ARQUIVOS:")
    print("=" * 50)
    
    try:
        files = client.files.list()
        
        if not files.data:
            print("📭 Nenhum arquivo para limpar")
            return
        
        deleted_count = 0
        for file in files.data:
            try:
                client.files.delete(file.id)
                print(f"✅ Removido: {file.filename} ({file.id})")
                deleted_count += 1
            except Exception as e:
                print(f"❌ Erro ao remover {file.filename}: {e}")
        
        print(f"\n🎉 {deleted_count} arquivos removidos")
        
    except Exception as e:
        print(f"❌ Erro na limpeza: {e}")

def check_assistant(client, assistant_id="asst_G8pkl29kFjPbAhYlS2kAclsU"):
    """Verifica status do assistente"""
    print("🤖 VERIFICANDO ASSISTENTE:")
    print("=" * 50)
    
    try:
        assistant = client.beta.assistants.retrieve(assistant_id)
        print(f"✅ Assistente encontrado:")
        print(f"   Nome: {assistant.name}")
        print(f"   ID: {assistant.id}")
        print(f"   Modelo: {assistant.model}")
        print(f"   Instruções: {len(assistant.instructions)} chars")
        
        # Verificar ferramentas
        if assistant.tools:
            print(f"   Ferramentas: {len(assistant.tools)}")
            for tool in assistant.tools:
                print(f"     - {tool.type}")
        
    except Exception as e:
        print(f"❌ Erro ao verificar assistente: {e}")

def cancel_runs(client, assistant_id="asst_G8pkl29kFjPbAhYlS2kAclsU"):
    """Cancela execuções em andamento"""
    print("⏹️ CANCELANDO EXECUÇÕES:")
    print("=" * 50)
    
    # Nota: Não há uma API direta para listar todas as execuções
    # Isso requer que você tenha os IDs das threads
    print("⚠️ Para cancelar execuções específicas, você precisa dos IDs das threads")
    print("💡 Se você tem IDs de execuções presas, adicione-os aqui manualmente")
    
    # Exemplo para cancelar uma execução específica:
    # thread_id = "thread_dlUSRqZ6Av8784yfFyErqIiA"
    # run_id = "run_kVHFmgjvFSqp6pElvS7zngBu"
    # 
    # try:
    #     client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run_id)
    #     print(f"✅ Execução cancelada: {run_id}")
    # except Exception as e:
    #     print(f"❌ Erro ao cancelar: {e}")

def main():
    """Função principal"""
    print("🔧 UTILITÁRIO DE LIMPEZA OPENAI")
    print("=" * 60)
    
    client = load_openai_client()
    
    while True:
        print("\n📋 OPÇÕES:")
        print("1. Listar arquivos")
        print("2. Limpar todos os arquivos")
        print("3. Verificar assistente")
        print("4. Cancelar execuções (manual)")
        print("5. Sair")
        
        choice = input("\n👉 Escolha uma opção (1-5): ").strip()
        
        if choice == "1":
            list_files(client)
        elif choice == "2":
            confirm = input("⚠️ Confirma limpeza de TODOS os arquivos? (s/N): ").strip().lower()
            if confirm == 's':
                cleanup_files(client)
            else:
                print("❌ Limpeza cancelada")
        elif choice == "3":
            check_assistant(client)
        elif choice == "4":
            cancel_runs(client)
        elif choice == "5":
            print("👋 Saindo...")
            break
        else:
            print("❌ Opção inválida")

if __name__ == "__main__":
    main()
