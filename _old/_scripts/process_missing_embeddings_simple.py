# =======================================================================
# PROCESSAMENTO DE EMBEDDINGS FALTANTES
# =======================================================================
# Script para processar embeddings das datas que não foram embeddadas
# usando o 04E_embedding_generation_optimized.py
# =======================================================================

import subprocess
import sys
import os
from datetime import datetime

# Datas que precisam ser processadas (baseado na planilha fornecida)
MISSING_DATES = [
    "2025-06-20",  # 1428 contratos
    "2025-06-19",  # 441 contratos  
    "2025-06-18",  # 6917 contratos
    "2025-06-17",  # 6635 contratos
    "2025-06-16",  # 5988 contratos
    "2025-06-15",  # 57 contratos
    "2025-06-14",  # 128 contratos
    "2025-06-13",  # 5879 contratos
    "2025-06-12",  # 6201 contratos
    "2025-06-11",  # 6455 contratos
    "2025-06-10",  # 6745 contratos
    "2025-06-09",  # 6537 contratos
    "2025-06-08",  # 56 contratos
    "2025-06-07",  # 128 contratos
    "2025-06-06",  # 6243 contratos
    "2025-06-05",  # 6449 contratos
    "2025-06-04",  # 6377 contratos
    "2025-06-03",  # 6701 contratos
    "2025-04-15",  # 6564 contratos
]

def print_safe(message):
    """Print seguro para evitar problemas de encoding"""
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode('ascii', 'replace').decode('ascii'))

def convert_date_format(date_str):
    """Converte data de YYYY-MM-DD para YYYYMMDD"""
    return date_str.replace("-", "")

def run_04E_for_date(date_str):
    """Executa o 04E para uma data específica"""
    script_path = os.path.join(os.path.dirname(__file__), "04E_embedding_generation_optimized.py")
    date_formatted = convert_date_format(date_str)
    
    print_safe(f"[{datetime.now().strftime('%H:%M:%S')}] Processando {date_str} (formato: {date_formatted})")
    
    try:
        # Executar o 04E com a data específica
        result = subprocess.run([
            sys.executable, 
            script_path, 
            "--test", date_formatted,
            "--debug"
        ], capture_output=True, text=True, timeout=1800)  # Timeout de 30 minutos
        
        if result.returncode == 0:
            print_safe(f"[{datetime.now().strftime('%H:%M:%S')}] SUCESSO {date_str}: Embeddings gerados")
            return True, "Success"
        else:
            print_safe(f"[{datetime.now().strftime('%H:%M:%S')}] ERRO {date_str}: Falha na geracao")
            # Não imprimir o stderr completo para evitar spam
            return False, "Error in 04E execution"
            
    except subprocess.TimeoutExpired:
        print_safe(f"[{datetime.now().strftime('%H:%M:%S')}] TIMEOUT {date_str}: 30 minutos")
        return False, "Timeout"
    except Exception as e:
        print_safe(f"[{datetime.now().strftime('%H:%M:%S')}] EXCECAO {date_str}: {str(e)}")
        return False, str(e)

def main():
    """Função principal"""
    print_safe("="*60)
    print_safe("PROCESSAMENTO DE EMBEDDINGS FALTANTES")
    print_safe("="*60)
    print_safe(f"Datas a processar: {len(MISSING_DATES)}")
    print_safe(f"Script: 04E_embedding_generation_optimized.py")
    print_safe(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_safe("="*60)
    
    # Estatísticas
    successful_dates = []
    failed_dates = []
    
    # Processar cada data
    for i, date_str in enumerate(MISSING_DATES, 1):
        print_safe(f"\n[{i:2d}/{len(MISSING_DATES)}] Iniciando processamento de {date_str}")
        
        success, output = run_04E_for_date(date_str)
        
        if success:
            successful_dates.append(date_str)
        else:
            failed_dates.append((date_str, output))
    
    # Relatório final
    print_safe("\n" + "="*60)
    print_safe("RELATORIO FINAL")
    print_safe("="*60)
    print_safe(f"Sucessos: {len(successful_dates)} datas")
    print_safe(f"Falhas: {len(failed_dates)} datas")
    print_safe(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if successful_dates:
        print_safe("\nDATAS PROCESSADAS COM SUCESSO:")
        for date in successful_dates:
            print_safe(f"  + {date}")
    
    if failed_dates:
        print_safe("\nDATAS COM FALHA:")
        for date, error in failed_dates:
            print_safe(f"  - {date}: {error}")
    
    print_safe(f"\nProcessamento concluido!")
    
    if failed_dates:
        print_safe(f"AVISO: Considere executar manualmente as datas com falha")
        return 1
    else:
        print_safe(f"Todos os embeddings foram gerados com sucesso!")
        return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_safe("\nProcessamento interrompido pelo usuario")
        sys.exit(130)
    except Exception as e:
        print_safe(f"\nErro inesperado: {e}")
        sys.exit(1)
