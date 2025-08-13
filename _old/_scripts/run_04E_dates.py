import subprocess
import sys
import os

# Datas em ordem crescente (YYYYMMDD)
DATES = [
    "20250415",  # 2025-04-15 - 6564 contratos
    "20250603",  # 2025-06-03 - 6701 contratos
    "20250604",  # 2025-06-04 - 6377 contratos
    "20250605",  # 2025-06-05 - 6449 contratos
    "20250606",  # 2025-06-06 - 6243 contratos
    "20250607",  # 2025-06-07 - 128 contratos
    "20250608",  # 2025-06-08 - 56 contratos
    "20250609",  # 2025-06-09 - 6537 contratos
    "20250610",  # 2025-06-10 - 6745 contratos
    "20250611",  # 2025-06-11 - 6455 contratos
    "20250612",  # 2025-06-12 - 6201 contratos
    "20250613",  # 2025-06-13 - 5879 contratos
    "20250614",  # 2025-06-14 - 128 contratos
    "20250615",  # 2025-06-15 - 57 contratos
    "20250616",  # 2025-06-16 - 5988 contratos
    "20250617",  # 2025-06-17 - 6635 contratos
    "20250618",  # 2025-06-18 - 6917 contratos
    "20250619",  # 2025-06-19 - 441 contratos
    "20250620",  # 2025-06-20 - 1428 contratos
]

def main():
    script_path = "04E_embedding_generation_optimized.py"
    
    print(f"Processando {len(DATES)} datas...")
    
    for i, date in enumerate(DATES, 1):
        print(f"\n[{i:2d}/{len(DATES)}] Processando data {date}")
        
        result = subprocess.run([
            sys.executable, 
            script_path, 
            "--test", date,
            "--debug"
        ])
        
        if result.returncode == 0:
            print(f"✓ Data {date}: OK")
        else:
            print(f"✗ Data {date}: ERRO")
    
    print("\nProcessamento concluido!")

if __name__ == "__main__":
    main()
