"""
Script principal para execução do sistema de geração de resumos em PDF
"""
import os
from dotenv import load_dotenv
from pdf_report_processor import PDFReportProcessor
from assistant_config import create_assistant, ASSISTANT_CONFIG
from openai import OpenAI

def setup_environment():
    """
    Configura o ambiente e carrega as variáveis
    """
    load_dotenv()
    
    api_key = os.getenv('OPENAI_API_KEY')
    assistant_id = os.getenv('ASSISTANT_ID')
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY não encontrada no arquivo .env")
    
    return api_key, assistant_id

def create_new_assistant_if_needed(api_key, assistant_id):
    """
    Cria um novo Assistant se necessário
    """
    if not assistant_id or assistant_id == 'your_assistant_id_here':
        print("Criando novo Assistant OpenAI...")
        client = OpenAI(api_key=api_key)
        assistant_id = create_assistant(client)
        
        # Atualizar arquivo .env
        with open('.env', 'r') as f:
            content = f.read()
        
        content = content.replace('your_assistant_id_here', assistant_id)
        
        with open('.env', 'w') as f:
            f.write(content)
        
        print(f"Assistant criado e salvo no .env: {assistant_id}")
    
    return assistant_id

def main():
    """
    Função principal do sistema
    """
    try:
        # Configurar ambiente
        api_key, assistant_id = setup_environment()
        
        # Criar Assistant se necessário
        assistant_id = create_new_assistant_if_needed(api_key, assistant_id)
        
        # Configurações do relatório
        pdf_path = input("Digite o caminho completo do PDF: ").strip().strip('"')
        
        if not os.path.exists(pdf_path):
            print(f"Arquivo não encontrado: {pdf_path}")
            return
        
        print("\nDigite o contexto adicional para o resumo:")
        print("(Exemplo: destacar crescimento, novos projetos, desafios, etc.)")
        user_prompt = input("Contexto: ").strip()
        
        if not user_prompt:
            user_prompt = "Gerar resumo executivo com os principais highlights do relatório."
        
        # Processar relatório
        print("\n" + "="*50)
        print("INICIANDO PROCESSAMENTO DO RELATÓRIO")
        print("="*50)
        
        processor = PDFReportProcessor(api_key, assistant_id)
        result_pdf = processor.process_report(pdf_path, user_prompt)
        
        print("\n" + "="*50)
        print("PROCESSAMENTO CONCLUÍDO!")
        print(f"Arquivo final: {result_pdf}")
        print("="*50)
        
    except Exception as e:
        print(f"Erro durante a execução: {e}")

if __name__ == "__main__":
    main()
