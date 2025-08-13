import os
import pandas as pd
import sqlite3
import json
from datetime import datetime
import time
from openai import OpenAI
import re
import traceback

# Variável de controle para debug
DEBUG = True

# Função auxiliar para logs de debug
def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

# Base paths - usando os mesmos caminhos do cv_v3
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_PATH = os.path.join(BASE_PATH, "DB")
DB_FILE = os.path.join(DB_PATH, "pncp_v2.db")
VALIDATION_PATH = os.path.join(BASE_PATH, "CLASSY", "CLASSY_ITENS", "VALIDATION")
os.makedirs(VALIDATION_PATH, exist_ok=True)

# Criar arquivo de resultados de validação com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
VALIDATION_FILE = os.path.join(VALIDATION_PATH, f"auto_validation_results_{TIMESTAMP}.xlsx")

# OpenAI configuration - usando a mesma chave do gvg_CL_reports_v3
client = OpenAI(api_key="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")

# ID do assistente CLASSY_VALIDATOR
assistant_id = "asst_mnqJ7xzDWphZXH18aOazymct"
model_id = "gpt-4o" 

# Criar um novo thread para a conversa
thread = client.beta.threads.create()
debug_print(f"Thread criado: {thread.id}")

# ===== FUNÇÕES DO ASSISTENTE (adaptadas de gvg_CL_reports_v3) =====

def send_user_message(content: str):
    """Envia uma mensagem do usuário para a thread, formatando em bloco de texto."""
    debug_print(f"Enviando mensagem para thread {thread.id[:8]}...: '{content[:100]}...'")
    formatted_content = [{"type": "text", "text": content}]
    try:
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=formatted_content
        )
        debug_print("Mensagem enviada com sucesso")
    except Exception as e:
        debug_print(f"Erro ao enviar mensagem: {str(e)}")
        raise

def poll_run():
    """Cria um run e aguarda a resposta do assistente."""
    debug_print(f"Iniciando run para thread {thread.id[:8]}...")
    try:
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant_id,
        )
        debug_print(f"Run finalizado com status: {run.status}")
        return run
    except Exception as e:
        debug_print(f"Erro no poll_run: {str(e)}")
        raise

def get_latest_assistant_message():
    """Retorna a mensagem do assistente na posição [0] da thread."""
    messages = list(client.beta.threads.messages.list(thread_id=thread.id))
    assistant_messages = [msg for msg in messages if msg.role == "assistant"]
    return assistant_messages[0] if assistant_messages else None

def get_assistant_response(user_query: str, max_retries=3):
    """
    Função genérica para enviar uma consulta ao assistente e obter sua resposta.
    Retorna o conteúdo da resposta ou None em caso de erro.
    """
    debug_print(f"Solicitando resposta para query: '{user_query[:100]}...'")
    
    for attempt in range(max_retries):
        try:
            send_user_message(user_query)
            run = poll_run()
            if run.status == 'completed':
                last_message = get_latest_assistant_message()
                if not last_message:
                    debug_print("Nenhuma mensagem de assistente recebida.")
                    return None
                debug_print("Resposta do assistente recebida com sucesso")
                return last_message
            else:
                debug_print(f"Run status não é 'completed': {run.status}")
                if attempt < max_retries - 1:
                    debug_print(f"Tentando novamente ({attempt+2}/{max_retries})...")
                    time.sleep(2)  # Pequeno atraso antes de tentar novamente
                else:
                    return None
        except Exception as e:
            debug_print(f"Erro ao obter resposta do assistente: {str(e)}")
            if attempt < max_retries - 1:
                debug_print(f"Tentando novamente ({attempt+2}/{max_retries})...")
                time.sleep(2)  # Pequeno atraso antes de tentar novamente
            else:
                return None

def extract_content_from_message(message):
    """Extrai o texto completo da resposta da mensagem do assistente."""
    try:
        if message is None:
            return ""
            
        content = message.content
        if not content:
            return ""
            
        text_parts = []
        for part in content:
            if hasattr(part, 'text') and hasattr(part.text, 'value'):
                text_parts.append(part.text.value)
            elif isinstance(part, dict) and 'text' in part:
                text_parts.append(part['text'])
        
        return ''.join(text_parts)
    except Exception as e:
        debug_print(f"Erro ao extrair conteúdo da mensagem: {str(e)}")
        return ""

def extract_choices_from_response(response_text):
    """Extrai a lista de índices da resposta do assistente."""
    debug_print(f"Extraindo escolhas da resposta: {response_text}")
    try:
        # Procurar por um padrão de lista no formato [n, n, ...]
        match = re.search(r'\[[\d,\s]*\]', response_text)
        if match:
            # Extrair a parte que corresponde à lista
            choices_str = match.group(0)
            # Converter para lista de inteiros usando json.loads
            choices = json.loads(choices_str)
            debug_print(f"Escolhas extraídas: {choices}")
            return choices
        else:
            debug_print("Nenhuma lista de escolhas encontrada na resposta")
            return []
    except Exception as e:
        debug_print(f"Erro ao extrair escolhas: {str(e)}")
        return []

# ===== FUNÇÕES DE CARREGAMENTO E SALVAMENTO DE DADOS =====

def load_data(limit=1000):
    """Carrega dados do banco de dados SQLite"""
    print(f"Conectando ao banco de dados: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    query = """
    SELECT ID, numeroControlePNCP, numeroItem, ID_ITEM_CONTRATACAO, descrição, item_type, 
    TOP_1, TOP_2, TOP_3, TOP_4, TOP_5, 
    SCORE_1, SCORE_2, SCORE_3, SCORE_4, SCORE_5, CONFIDENCE 
    FROM item_classificacao
    ORDER BY RANDOM()
    """
    
    if limit:
        query += f" LIMIT {limit}"
        
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print(f"Dados carregados: {len(df)} itens")
    return df

def save_validation_results(validation_results, partial=False):
    """Salva os resultados da validação em um arquivo Excel"""
    if not validation_results:
        print("Nenhum resultado para salvar.")
        return False
    
    # Determinar nome do arquivo (parcial ou final)
    file_path = VALIDATION_FILE
    if partial:
        file_path = VALIDATION_FILE.replace('.xlsx', f'_partial_{len(validation_results)}.xlsx')
    
    try:
        # Salvar em Excel
        results_df = pd.DataFrame(validation_results)
        results_df.to_excel(file_path, index=False)
        print(f"Resultados salvos em: {file_path}")
        
        # Também salvar como JSON para backup
        json_file = file_path.replace('.xlsx', '.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(validation_results, f, indent=2, ensure_ascii=False)
        print(f"Backup JSON salvo em: {json_file}")
        
        return True
    except Exception as e:
        print(f"Erro ao salvar resultados: {e}")
        return False

# ===== FUNÇÃO PARA CONSTRUIR O PROMPT =====

def build_prompt(item_data):
    """Constrói o prompt para o assistente no formato especificado"""
    prompt = f"""
Você é um assistente especialista em classificação de itens de compra governamental. Sua tarefa é analisar a descrição de um item e, a partir de uma lista de até 5 categorias sugeridas, selecionar quais categorias são as mais relevantes e em que ordem de preferência.

**Descrição do Item:**
"{item_data['descrição']}"

**Categorias Sugeridas (com seus índices originais de 0 a 4):**
0: "{item_data['TOP_1']}" (Score: {item_data['SCORE_1']:.4f})
1: "{item_data['TOP_2']}" (Score: {item_data['SCORE_2']:.4f})
2: "{item_data['TOP_3']}" (Score: {item_data['SCORE_3']:.4f})
3: "{item_data['TOP_4']}" (Score: {item_data['SCORE_4']:.4f})
4: "{item_data['TOP_5']}" (Score: {item_data['SCORE_5']:.4f})

**Confiança Geral das Sugestões:** {item_data['CONFIDENCE']:.2f}%

**Instruções para Saída:**
- Analise a "Descrição do Item" e compare-a com cada "Categoria Sugerida".
- Decida quais categorias são as mais relevantes e determine a sua ordem de preferência (a mais relevante primeiro).
- Sua resposta DEVE ser uma lista de índices (números de 0 a 4) das categorias que você selecionou, na sua ordem de preferência, formatada exatamente como: `[índice1, índice2, ...]`.
- Se nenhuma categoria for relevante, retorne uma lista vazia: `[]`.
- Se, por exemplo, você achar que a categoria de índice 0 é a mais relevante, seguida pela de índice 3, sua saída deve ser: `[0, 3]`.

**Sua Saída (lista de índices no formato `[índice1, índice2, ...]`):**
"""
    return prompt

# ===== FUNÇÃO PARA PROCESSAR ITENS =====

def process_items(df, batch_size=None):
    """Processa e valida um lote de itens"""
    validation_results = []
    total_items = len(df) if batch_size is None else min(batch_size, len(df))
    
    print(f"Iniciando processamento de {total_items} itens...")
    
    for i, (_, item) in enumerate(df.head(total_items).iterrows()):
        print(f"Processando item {i+1}/{total_items}: {item['ID_ITEM_CONTRATACAO']}")
        item_data = item.to_dict()
        
        # Construir o prompt para o assistente
        prompt = build_prompt(item_data)
        
        # Obter a validação do assistente
        assistant_message = get_assistant_response(prompt)
        
        if assistant_message:
            # Extrair o texto da resposta
            response_text = extract_content_from_message(assistant_message)
            print(f"  → Resposta: {response_text.strip()[:100]}")
            
            # Extrair as escolhas da resposta
            validated_choices_indices = extract_choices_from_response(response_text)
            print(f"  → Validação extraída: {validated_choices_indices}")
        else:
            print("  → Falha ao obter resposta do assistente")
            validated_choices_indices = []
        
        # Extrair as categorias validadas na ordem correta
        validated_categories = []
        for idx in validated_choices_indices:
            if 0 <= idx <= 4:  # Verificar se o índice é válido
                category_key = f'TOP_{idx+1}'
                validated_categories.append(item_data[category_key])
        
        # Montar o registro de validação no mesmo formato que cv_v3.py
        validation_item = {
            'ID': item_data['ID'],
            'numeroControlePNCP': item_data['numeroControlePNCP'],
            'numeroItem': item_data['numeroItem'],
            'ID_ITEM_CONTRATACAO': item_data['ID_ITEM_CONTRATACAO'],
            'descrição': item_data['descrição'],
            'item_type': item_data['item_type'],
            'original_top_1': item_data['TOP_1'],
            'original_top_2': item_data['TOP_2'],
            'original_top_3': item_data['TOP_3'],
            'original_top_4': item_data['TOP_4'],
            'original_top_5': item_data['TOP_5'],
            'original_score_1': item_data['SCORE_1'],
            'original_score_2': item_data['SCORE_2'],
            'original_score_3': item_data['SCORE_3'],
            'original_score_4': item_data['SCORE_4'],
            'original_score_5': item_data['SCORE_5'],
            'original_confidence': item_data['CONFIDENCE'],
            'validated_choices_indices': validated_choices_indices,
            'validated_top_1': validated_categories[0] if len(validated_categories) > 0 else None,
            'validated_top_2': validated_categories[1] if len(validated_categories) > 1 else None,
            'validated_top_3': validated_categories[2] if len(validated_categories) > 2 else None,
            'validated_top_4': validated_categories[3] if len(validated_categories) > 3 else None,
            'validated_top_5': validated_categories[4] if len(validated_categories) > 4 else None,
            'validation_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'validation_method': 'auto_ai'  # Marcar que foi validação automática
        }
        
        validation_results.append(validation_item)
        
        # Salvar resultados parciais a cada 10 itens
        if (i+1) % 10 == 0:
            save_validation_results(validation_results, partial=True)
    
    return validation_results

# ===== FUNÇÃO PRINCIPAL =====

def main():
    print("=== Auto-Validador de Classificações com CLASSY_VALIDATOR ===")
    
    # Perguntar se deseja limitar o número de itens
    limit_str = input("Número de itens para processar (Enter para todos): ")
    limit = int(limit_str) if limit_str.strip() else None
    
    # Carregar dados
    items_df = load_data(limit)
    
    if len(items_df) == 0:
        print("Nenhum item encontrado na base de dados!")
        return
    
    # Processar os itens
    validation_results = process_items(items_df)
    
    # Salvar resultados finais
    success = save_validation_results(validation_results)
    
    if success:
        print(f"\nProcessamento concluído. {len(validation_results)} itens validados.")
        print(f"Resultados salvos em: {VALIDATION_FILE}")
    else:
        print("\nErro ao salvar os resultados!")

if __name__ == "__main__":
    main()