import re

# Caminho do arquivo de log
log_file_path = r'c:\Users\Haroldo Duraes\Desktop\Scripts\GovGo\v1\scripts\logs\log_cron_job_20250922.log'

# Ler o conteúdo do arquivo
with open(log_file_path, 'r', encoding='utf-8') as file:
    log_content = file.readlines()

# Remover datas e horários usando regex
cleaned_log = [re.sub(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z ', '', line) for line in log_content]

# Salvar o log limpo em um novo arquivo
cleaned_log_file_path = log_file_path.replace('.log', '_cleaned.log')
with open(cleaned_log_file_path, 'w', encoding='utf-8') as file:
    file.writelines(cleaned_log)

print(f"Log limpo salvo em: {cleaned_log_file_path}")