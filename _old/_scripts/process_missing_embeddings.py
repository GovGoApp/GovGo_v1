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

# Console simples para evitar problemas de encoding no Windows
class SimpleConsole:
    def print(self, message):
        try:
            print(message)
        except UnicodeEncodeError:
            # Fallback para ASCII
            print(message.encode('ascii', 'replace').decode('ascii'))

console = SimpleConsole()

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

def convert_date_format(date_str):
    """Converte data de YYYY-MM-DD para YYYYMMDD"""
    return date_str.replace("-", "")

def run_04E_for_date(date_str):
    """Executa o 04E para uma data específica"""
    script_path = os.path.join(os.path.dirname(__file__), "04E_embedding_generation_optimized.py")
    date_formatted = convert_date_format(date_str)
    
    console.print(f"Processando embeddings para {date_str} (formato: {date_formatted})")
    
    try:
        # Executar o 04E com a data específica
        result = subprocess.run([
            sys.executable, 
            script_path, 
            "--test", date_formatted,
            "--debug"
        ], capture_output=True, text=True, timeout=1800)  # Timeout de 30 minutos
        
        if result.returncode == 0:
            console.print(f"SUCESSO {date_str}: Embeddings gerados com sucesso")
            return True, result.stdout
        else:
            console.print(f"ERRO {date_str}: Erro na geração de embeddings")
            console.print(f"STDERR: {result.stderr}")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        console.print(f"TIMEOUT {date_str}: Timeout após 30 minutos")
        return False, "Timeout"
    except Exception as e:
        console.print(f"EXCECAO {date_str}: Exceção: {e}")
        return False, str(e)

def main():
    """Função principal"""
    console.print(Panel.fit(
        f"Processamento de Embeddings Faltantes\n"
        f"Datas a processar: {len(MISSING_DATES)}\n"
        f"Script: 04E_embedding_generation_optimized.py",
        title="EMBEDDINGS FALTANTES",
        style="bold blue"
    ))
    
    # Estatísticas
    successful_dates = []
    failed_dates = []
    
    # Processar cada data
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Processando datas...", total=len(MISSING_DATES))
        
        for i, date_str in enumerate(MISSING_DATES, 1):
            progress.update(task, description=f"Data {i}/{len(MISSING_DATES)}: {date_str}")
            
            success, output = run_04E_for_date(date_str)
            
            if success:
                successful_dates.append(date_str)
            else:
                failed_dates.append((date_str, output))
            
            progress.advance(task)
    
    # Relatório final
    console.print("\n" + "="*60)
    console.print(f"RELATORIO FINAL")
    console.print("="*60)
    console.print(f"Sucessos: {len(successful_dates)} datas")
    console.print(f"Falhas: {len(failed_dates)} datas")
    
    if successful_dates:
        console.print("\nDATAS PROCESSADAS COM SUCESSO:")
        for date in successful_dates:
            console.print(f"  + {date}")
    
    if failed_dates:
        console.print("\nDATAS COM FALHA:")
        for date, error in failed_dates:
            console.print(f"  - {date}: {error[:100]}...")
    
    console.print(f"\nProcessamento concluido!")
    
    if failed_dates:
        console.print(f"AVISO: Considere executar manualmente as datas com falha")
        return 1
    else:
        console.print(f"Todos os embeddings foram gerados com sucesso!")
        return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\nProcessamento interrompido pelo usuario")
        sys.exit(130)
    except Exception as e:
        console.print(f"\nErro inesperado: {e}")
        sys.exit(1)
