### EMB_NV2_v6.3 (EMBEDDING NIVEL 2 V6.3) ###

# Este script é responsável por gerar embeddings para itens de compras e classificá-los em categorias de materiais e serviços.
# Modificações:
# - Implementação com API HTTP do LMStudio para embeddings
# - Checkpoints salvos com timestamps únicos para preservar histórico de execuções
# - Otimização do processamento paralelo com número ideal de workers
# - Normalização de vetores para cálculo de similaridade por cosseno
# - Opção para desabilitar ou resumir estatisticamente os embeddings dos itens

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn, TaskProgressColumn
from concurrent.futures import ThreadPoolExecutor
import threading
import pickle
import time
import requests  # Para requisições HTTP

# Criar uma instância de console para exibição formatada
console = Console()


# Definir caminhos e arquivos
PATH = "C:\\Users\\Haroldo Duraes\\"
BASE_PATH = PATH + "Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = BASE_PATH + "CAT\\"
CLASS_PATH = BASE_PATH + "CLASSIFICAÇÃO\\"
EMBEDDING_PATH = BASE_PATH + "EMBEDDING\\"
ITEMS_EMBED_PATH = EMBEDDING_PATH + "ITENS\\"

# Definição do endpoint e modelo
API_URL = "http://127.0.0.1:1234/v1/embeddings"
#MODEL_NAME = "text-embedding-nomic-embed-text-v1.5"
#MODEL_NAME = "text-embedding-granite-embedding-278m-multilingual"
#MODEL_NAME = "qwen-2.5-1.5b-embedding-entropy-rl-1"
#MODEL_NAME = "text-embedding-granite-embedding-107m-multilingual"
MODEL_NAME = "jina-embeddings-v3"


console.print(f"[bold blue]Usando API HTTP: {API_URL}")
console.print(f"[bold blue]Modelo selecionado: {MODEL_NAME}")

#EXCEL_FILE = CLASS_PATH + "CONTRATACAO_ID_ITENS_TOTAL.xlsx"
EXCEL_FILE = CLASS_PATH + "TESTE_SIMPLES.xlsx"
CATMAT_FILE = CAT_PATH + "CATMAT_nv2.json"
CATSER_FILE = CAT_PATH + "CATSER_nv2.json"

SHEET = "OBJETOS"

# Nome do arquivo de saída com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')

OUTPUT_FILE = CLASS_PATH + f"CLASSIFICACAO_{MODEL_NAME}_{TIMESTAMP}.xlsx"
CHECKPOINT_FILE = CLASS_PATH + f"CHECKPOINT_EMB_{TIMESTAMP}.pkl"
BATCH_SIZE = 20000  # Tamanho do batch para processamento e salvamento

# Caminhos para armazenamento de embeddings
CATMAT_EMBED_FILE = EMBEDDING_PATH + f"catmat_embeddings_{MODEL_NAME.replace('-', '_')}.pkl"
CATSER_EMBED_FILE = EMBEDDING_PATH + f"catser_embeddings_{MODEL_NAME.replace('-', '_')}.pkl"

SAVE_ITEM_EMBEDDINGS = False

# Criar diretórios se não existirem
for directory in [EMBEDDING_PATH, ITEMS_EMBED_PATH]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Constantes para controle de execução
MAX_WORKERS = min(32, os.cpu_count() * 4)  # Número de threads para processamento paralelo
console.print("CPU: " + str(os.cpu_count()))
console.print("WORKERS = " + str(MAX_WORKERS))

# Criar lock para acessos concorrentes
results_lock = threading.Lock()
checkpoint_lock = threading.Lock()
embedding_lock = threading.Lock()
http_lock = threading.Lock()  # Para requests HTTP thread-safe

def get_embedding_http(text):
    """Obter embedding para um texto usando a API HTTP"""
    with http_lock:
        try:
            headers = {"Content-Type": "application/json"}
            data = {
                "model": MODEL_NAME,
                "input": text
            }
            
            response = requests.post(API_URL, headers=headers, json=data)
            response.raise_for_status()  # Verificar se a requisição foi bem-sucedida
            
            result = response.json()
            return np.array(result["data"][0]["embedding"])
        except Exception as e:
            console.print(f"[bold red]Erro na requisição HTTP: {str(e)}[/bold red]")
            if "response" in locals():
                console.print(f"[bold red]Resposta: {response.text}[/bold red]")
            
            # Instruções detalhadas em caso de erro
            console.print("\n[bold yellow]INSTRUÇÕES PARA RESOLVER:[/bold yellow]")
            console.print("1. Verifique se o LM Studio está aberto")
            console.print("2. Na opção Embeddings, selecione o modelo e clique em START")
            console.print("3. Certifique-se que o servidor está rodando em http://127.0.0.1:1234")
            console.print("4. Tente novamente após iniciar o servidor\n")
            
            raise
    
def save_embeddings(embeddings, filepath):
    """Salva embeddings em arquivo pickle."""
    with embedding_lock:
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(embeddings, f)
            console.print(f"[green]Embeddings salvos em {filepath}[/green]")
            return True
        except Exception as e:
            console.print(f"[bold red]Erro ao salvar embeddings: {str(e)}[/bold red]")
            return False

def load_embeddings(filepath):
    """Carrega embeddings de arquivo pickle se existir."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                embeddings = pickle.load(f)
            console.print(f"[green]Embeddings carregados de {filepath}[/green]")
            return embeddings
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar embeddings: {str(e)}[/bold red]")
    return None

def load_data():
    """Carregar dados do Excel e arquivos de catálogo."""
    console.print("[bold magenta]Carregando dados...[/bold magenta]")
    
    # Verificar se existe um checkpoint para continuar o processamento
    checkpoint = load_checkpoint()
    if checkpoint:
        console.print("[bold yellow]Checkpoint encontrado. Continuando do último processamento...[/bold yellow]")
        last_processed = checkpoint['last_processed']
        
        # Carregar apenas as linhas ainda não processadas
        try:
            # Primeiro, verificamos o tamanho total para calcular o offset
            total_rows = pd.read_excel(EXCEL_FILE, sheet_name=SHEET, nrows=0).shape[0]
            
            # Depois carregamos apenas as linhas restantes
            skiprows = list(range(1, last_processed + 1))  # Pular cabeçalho + linhas já processadas
            df_items = pd.read_excel(EXCEL_FILE, sheet_name=SHEET, skiprows=skiprows)
            console.print(f"[green]Carregados {len(df_items)} itens restantes do Excel (a partir da linha {last_processed+1}).[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar arquivo Excel: {str(e)}[/bold red]")
            raise
    else:
        # Carregar do início
        try:
            df_items = pd.read_excel(EXCEL_FILE, sheet_name=SHEET)
            console.print(f"[green]Carregados {len(df_items)} itens do Excel.[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar arquivo Excel: {str(e)}[/bold red]")
            raise
    
    # Carregar catálogos
    try:
        with open(CATMAT_FILE, 'r', encoding='utf-8') as f:
            catmat = json.load(f)
        with open(CATSER_FILE, 'r', encoding='utf-8') as f:
            catser = json.load(f)
        console.print(f"[green]Carregados {len(catmat)} grupos CATMAT e {len(catser)} grupos CATSER.[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar arquivos de catálogo: {str(e)}[/bold red]")
        raise
    
    # Se temos checkpoint, precisamos também carregar os resultados já processados
    if checkpoint and 'output_file' in checkpoint:
        try:
            existing_results = pd.read_excel(checkpoint['output_file'])
            console.print(f"[green]Carregados {len(existing_results)} resultados anteriores.[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar resultados anteriores: {str(e)}[/bold red]")
            existing_results = pd.DataFrame()
    else:
        existing_results = pd.DataFrame()
    
    return df_items, catmat, catser, existing_results, checkpoint

def save_checkpoint(last_processed, output_file):
    """Salvar checkpoint para continuar processamento posteriormente usando timestamp único."""
    with checkpoint_lock:
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'last_processed': last_processed,
            'output_file': output_file
        }
        
        # Usar timestamp único para cada checkpoint
        check_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        checkpoint_file = CHECKPOINT_FILE.replace('.pkl', f'_{check_timestamp}.pkl')
        
        with open(checkpoint_file, 'wb') as f:
            pickle.dump(checkpoint, f)
        console.print(f"[green]Checkpoint salvo em: {checkpoint_file}[/green]")

def load_checkpoint():
    """Carregar checkpoint se existir."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'rb') as f:
            return pickle.load(f)
    return None

def prepare_catalog_entries(catmat, catser):
    """Preparar entradas de catálogo combinadas para embedding."""
    console.print("[bold magenta]Preparando textos de catálogo...[/bold magenta]")
    
    catmat_texts = []
    catmat_meta = []  # Vai armazenar tuplas (catalog, group_code, group_name, class_code, class_name)
    
    with Progress(
        SpinnerColumn(), 
        TextColumn("[bold cyan]Processando CATMAT..."),
        BarColumn(), 
        TaskProgressColumn(), 
        TimeElapsedColumn()
    ) as progress:
        task = progress.add_task("", total=len(catmat))
        
        for group in catmat:
            grp_code = group.get('codGrupo')
            grp_name = group.get('Grupo')
            for cls in group.get('Classes', []):
                class_code = cls.get('codClasse')
                class_name = cls.get('Classe')
                # Combinar nomes de grupo e classe para texto de embedding (materiais)
                combined_text = f"{grp_name} - {class_name}"
                catmat_texts.append(combined_text)
                catmat_meta.append(("MATERIAL", grp_code, grp_name, class_code, class_name))
            progress.update(task, advance=1)
    
    catser_texts = []
    catser_meta = []
    
    with Progress(
        SpinnerColumn(), 
        TextColumn("[bold cyan]Processando CATSER..."),
        BarColumn(), 
        TaskProgressColumn(), 
        TimeElapsedColumn()
    ) as progress:
        task = progress.add_task("", total=len(catser))
        
        for group in catser:
            grp_code = group.get('codGrupo')
            grp_name = group.get('Grupo')
            for cls in group.get('Classes', []):
                class_code = cls.get('codClasse')
                class_name = cls.get('Classe')
                # Combinar nomes de grupo e classe para texto de embedding (serviços)
                combined_text = f"{grp_name} - {class_name}"
                catser_texts.append(combined_text)
                catser_meta.append(("SERVIÇO", grp_code, grp_name, class_code, class_name))
            progress.update(task, advance=1)
    
    console.print(f"[green]Preparados {len(catmat_texts)} textos de categoria CATMAT para embedding.[/green]")
    console.print(f"[green]Preparados {len(catser_texts)} textos de categoria CATSER para embedding.[/green]")
    
    return catmat_texts, catmat_meta, catser_texts, catser_meta

def get_embeddings(texts, batch_size=32, show_progress=True):
    """Gerar embeddings para uma lista de textos usando a API HTTP."""
    embeddings = []
    
    # Processar em lotes para evitar estouro de memória
    total_batches = int(np.ceil(len(texts) / batch_size))
    
    # Testar a conexão primeiro com um texto simples
    try:
        console.print("[bold yellow]Testando conexão com servidor de embeddings...[/bold yellow]")
        test_emb = get_embedding_http("Teste de conexão")
        console.print(f"[green]Conexão com servidor estabelecida! (dimensão do embedding: {len(test_emb)})[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao testar conexão: {str(e)}[/bold red]")
        raise
    
    # Determinar como processar - com ou sem barra de progresso
    if show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Processando embeddings..."),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn()
        ) as progress:
            task = progress.add_task("", total=total_batches)
            
            # Loop de processamento com progresso visível
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                
                # Obter embeddings via API HTTP
                batch_embeddings = []
                for text in batch:
                    emb = get_embedding_http(text)
                    batch_embeddings.append(emb)
                
                embeddings.extend(batch_embeddings)
                progress.update(task, advance=1)
    else:
        # Loop de processamento sem progresso visível
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = []
            for text in batch:
                emb = get_embedding_http(text)
                batch_embeddings.append(emb)
            embeddings.extend(batch_embeddings)
    
    return embeddings

def classify_items_batched(df_items, catmat_embeddings, catmat_meta, catser_embeddings, catser_meta, 
                          existing_results=None, last_processed=0, top_n=5):
    """Classificar itens em batches com processamento paralelo eficiente."""
    
    # Pré-computar matrizes numpy para cálculo de similaridade mais rápido
    catmat_matrix = np.vstack(catmat_embeddings)
    catser_matrix = np.vstack(catser_embeddings)
    
    # Inicializar resultados acumulados
    all_results = existing_results if existing_results is not None else pd.DataFrame()
    total_items = len(df_items)
    
    # Processar em batches para salvar resultados incrementalmente
    for batch_start in range(0, total_items, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_items)
        df_batch = df_items.iloc[batch_start:batch_end]
        
        console.print(f"[bold magenta]Processando batch {batch_start//BATCH_SIZE + 1}/{total_items//BATCH_SIZE + 1} "
                     f"(itens {batch_start+1}-{batch_end}/{total_items})[/bold magenta]")
        
        # 1. Primeiro, extrair todas as descrições do batch de uma vez
        descriptions = []
        item_ids = []
        indices = []
        
        for idx, row in df_batch.iterrows():
            item_id = row.get("id") or row.get("id_pncp")
            description = str(row.get("objetoCompra") or "")
            
            if not description or pd.isna(description) or description.lower() in ["nan", "none"]:
                # Itens inválidos ainda precisam de um placeholder
                descriptions.append("")
            else:
                descriptions.append(description)
            
            item_ids.append(item_id)
            indices.append(idx)
        
        # 2. Obter embeddings para todo o batch de uma vez
        console.print("[bold cyan]Obtendo embeddings para todo o batch...[/bold cyan]")
        
        try:
            # Obter embeddings apenas para descrições não vazias
            valid_indices = [i for i, desc in enumerate(descriptions) if desc]
            valid_descriptions = [descriptions[i] for i in valid_indices]
            
            if valid_descriptions:
                # Obter embeddings usando a API HTTP
                item_embeddings = get_embeddings(valid_descriptions, batch_size=32, show_progress=True)
                
                # Mapear de volta para o índice original
                all_item_embeddings = [None] * len(descriptions)
                for i, emb in zip(valid_indices, item_embeddings):
                    all_item_embeddings[i] = emb
                
                # Salvar embeddings dos itens
                if SAVE_ITEM_EMBEDDINGS:
                    # Salvar apenas um resumo dos embeddings (médias e desvios padrão)
                    embeddings_summary = {
                        'batch': f"{batch_start}_{batch_end}",
                        'timestamp': TIMESTAMP,
                        'model': MODEL_NAME,
                        'num_items': len(valid_indices),
                        'mean_vector': np.mean([emb for emb in item_embeddings], axis=0).tolist() if item_embeddings else None,
                        'std_vector': np.std([emb for emb in item_embeddings], axis=0).tolist() if item_embeddings else None
                    }
                    
                    # Salvar um arquivo mais compacto com apenas o resumo
                    summary_file = f"{ITEMS_EMBED_PATH}SUMMARY_{batch_start}_{batch_end}_{MODEL_NAME.replace('-', '_')}_{TIMESTAMP}.pkl"
                    save_embeddings(embeddings_summary, summary_file)
                    console.print(f"[green]Resumo de embeddings salvo em: {summary_file}[/green]")
            else:
                all_item_embeddings = []
                
        except Exception as e:
            console.print(f"[bold red]Erro ao gerar embeddings do batch: {str(e)}[/bold red]")
            import traceback
            console.print(traceback.format_exc())
            continue
        
        # 3. Agora vamos distribuir o trabalho de classificação (puramente local) entre os workers
        console.print("[bold cyan]Classificando com processamento paralelo...[/bold cyan]")
        
        # Preparar argumentos para classificação
        classification_args = []
        for i, (idx, item_id, description) in enumerate(zip(indices, item_ids, descriptions)):
            # Se temos embedding válido para este item
            if i < len(all_item_embeddings) and all_item_embeddings[i] is not None:
                item_emb = all_item_embeddings[i]
                classification_args.append((idx, item_id, description, item_emb, catmat_matrix, 
                                         catser_matrix, catmat_meta, catser_meta, top_n))
            else:
                # Item inválido ou sem embedding
                classification_args.append((idx, item_id, description, None, None, None, None, None, top_n))
        
        # Usar ThreadPoolExecutor para classificação paralela (puramente local)
        batch_results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Classificando items..."),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn()
        ) as progress:
            task_items = progress.add_task("", total=len(classification_args))
            
            # Usar mais workers aqui é realmente benéfico para cálculos locais!
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [executor.submit(classify_item_local, args) for args in classification_args]
                
                for future in futures:
                    try:
                        idx, item_id, result = future.result()
                        batch_results.append(result)
                        progress.update(task_items, advance=1)
                    except Exception as e:
                        console.print(f"[bold red]Erro em future: {str(e)}[/bold red]")
                        progress.update(task_items, advance=1)
        
        # Converter resultados do batch em DataFrame
        df_batch_results = pd.DataFrame(batch_results)
        
        # Processar as categorias top N e outros campos antes de salvar
        if 'categoriasTopN' in df_batch_results.columns:
            df_batch_results['categoriasTopN'] = df_batch_results['categoriasTopN'].apply(
                lambda x: '\n'.join(x) if isinstance(x, list) else str(x))
        
        # Remover a coluna embedding antes de salvar no Excel (muito grande para Excel)
        if 'embedding' in df_batch_results.columns:
            df_batch_results = df_batch_results.drop(columns=['embedding'])
        
        # Adicionar aos resultados acumulados
        all_results = pd.concat([all_results, df_batch_results], ignore_index=True)
        
        # Salvar resultados incrementais
        temp_output = OUTPUT_FILE.replace('.xlsx', f'_incremental.xlsx')
        try:
            all_results.to_excel(temp_output, index=False)
            console.print(f"[green]Salvo incrementalmente: {temp_output} "
                         f"({len(all_results)} itens processados)[/green]")
            
            # Atualizar checkpoint para recuperação
            save_checkpoint(
                last_processed + batch_end,  # Atualizar o número de linhas processadas
                temp_output  # Salvar o caminho do arquivo incremental
            )
        except Exception as e:
            console.print(f"[bold red]Erro ao salvar resultados incrementais: {str(e)}[/bold red]")
    
    # Mover a coluna de score para melhor visualização
    cols = all_results.columns.tolist()
    if "scoreCategoria" in cols:
        cols.remove("scoreCategoria")
        cols.insert(cols.index("categoriasTopN") if "categoriasTopN" in cols else -1, "scoreCategoria")
        all_results = all_results[cols]
    
    # Salvar versão final
    try:
        all_results.to_excel(OUTPUT_FILE, index=False)
        console.print(f"[bold green]Resultados finais salvos em: {OUTPUT_FILE}[/bold green]")
        
        # Remover arquivo incremental após sucesso, mas manter checkpoints
        if os.path.exists(temp_output):
            os.remove(temp_output)
    except Exception as e:
        console.print(f"[bold red]Erro ao salvar resultados finais: {str(e)}[/bold red]")
    
    return all_results

def normalize_vectors(vectors):
    """Normaliza vetores para calcular similaridade por produto escalar."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / norms

def classify_item_local(args):
    """Função para classificação local com normalização de vetores."""
    idx, item_id, description, item_emb, catmat_matrix, catser_matrix, catmat_meta, catser_meta, top_n = args
    
    # Se não temos embedding, é um item inválido
    if item_emb is None:
        return idx, item_id, {
            "id": item_id,
            "objetoCompra": description,
            "tipoDetectado": "Não classificado",
            "categoriaMelhor": "Descrição inválida",
            "scoreCategoria": 0.0,
            "categoriasTopN": [],
            "embedding": None  # Incluir embedding nulo para consistência
        }
    
    try:
        # Normalizar o vetor do item para garantir similaridade por cosseno
        item_emb_norm = item_emb / np.linalg.norm(item_emb)
        
        # Calcular similaridade com CATMAT e CATSER (operação puramente local e rápida)
        catmat_scores = catmat_matrix.dot(item_emb_norm)
        catser_scores = catser_matrix.dot(item_emb_norm)
        
        # Identificar melhor correspondência em cada catálogo
        best_mat_idx = int(np.argmax(catmat_scores))
        best_ser_idx = int(np.argmax(catser_scores))
        best_mat_score = float(catmat_scores[best_mat_idx])
        best_ser_score = float(catser_scores[best_ser_idx])
        
        # Determinar tipo pela maior similaridade
        if best_mat_score >= best_ser_score:
            tipo = "Material"
            best_idx = best_mat_idx
            best_meta = catmat_meta[best_idx]
            # Obter top N categorias de material
            top_indices = np.argsort(catmat_scores)[-top_n:][::-1]
            top_matches = [(catmat_meta[i], float(catmat_scores[i])) for i in top_indices]
        else:
            tipo = "Serviço"
            best_idx = best_ser_idx
            best_meta = catser_meta[best_idx]
            # Obter top N categorias de serviço
            top_indices = np.argsort(catser_scores)[-top_n:][::-1]
            top_matches = [(catser_meta[i], float(catser_scores[i])) for i in top_indices]
        
        # Formatar a melhor categoria
        catalog_label, grp_code, grp_name, class_code, class_name = best_meta
        best_category_str = f"{catalog_label}; {grp_code}-{grp_name}; {class_code}-{class_name}"
        
        # Formatar lista top N como strings com scores
        top_list_str = []
        for meta, score in top_matches:
            cat_label, g_code, g_name, c_code, c_name = meta
            cat_str = f"{cat_label}; {g_code}-{g_name}; {c_code}-{c_name} (score={score:.3f})"
            top_list_str.append(cat_str)
        
        return idx, item_id, {
            "id": item_id,
            "objetoCompra": description,
            "tipoDetectado": tipo,
            "categoriaMelhor": best_category_str,
            "scoreCategoria": float(best_mat_score if tipo == "Material" else best_ser_score),
            "categoriasTopN": top_list_str,
            "embedding": item_emb.tolist()  # Converter para lista para poder serializar
        }
    except Exception as e:
        console.print(f"[bold red]Erro na classificação do item {item_id}: {str(e)}[/bold red]")
        return idx, item_id, {
            "id": item_id,
            "objetoCompra": description,
            "tipoDetectado": "Erro",
            "categoriaMelhor": f"Erro: {str(e)}",
            "scoreCategoria": 0.0,
            "categoriasTopN": [],
            "embedding": None  # Incluir embedding nulo para consistência
        }

def main():
    start_time = time.time()
    
    try:
        # Carregar dados e verificar se existe checkpoint
        df_items, catmat, catser, existing_results, checkpoint = load_data()
        last_processed = checkpoint['last_processed'] if checkpoint else 0
        
        # Preparar textos de catálogo para embeddings
        catmat_texts, catmat_meta, catser_texts, catser_meta = prepare_catalog_entries(catmat, catser)
        print(catser_texts[:5])
        print(catmat_texts[:5])
        # Verificar se há embeddings de catálogo pré-existentes
        console.print("[bold magenta]Verificando embeddings de catálogo existentes...[/bold magenta]")
        
        catmat_embeddings = load_embeddings(CATMAT_EMBED_FILE)
        if catmat_embeddings is None or len(catmat_embeddings) != len(catmat_texts):
            console.print(f"[yellow]Embeddings de CATMAT não encontrados ou desatualizados. Gerando novos com {MODEL_NAME}...[/yellow]")
            catmat_embeddings = get_embeddings(catmat_texts)
            save_embeddings(catmat_embeddings, CATMAT_EMBED_FILE)
        
        catser_embeddings = load_embeddings(CATSER_EMBED_FILE)
        if catser_embeddings is None or len(catser_embeddings) != len(catser_texts):
            console.print(f"[yellow]Embeddings de CATSER não encontrados ou desatualizados. Gerando novos com {MODEL_NAME}...[/yellow]")
            catser_embeddings = get_embeddings(catser_texts)
            save_embeddings(catser_embeddings, CATSER_EMBED_FILE)
        
        # Normalizar as matrizes de embeddings para similaridade por cosseno
        console.print("[cyan]Normalizando vetores para cálculo de similaridade por cosseno...[/cyan]")
        catmat_embeddings = [emb / np.linalg.norm(emb) for emb in catmat_embeddings]
        catser_embeddings = [emb / np.linalg.norm(emb) for emb in catser_embeddings]
        
        console.print("[green]Embeddings de categorias preparados.[/green]")
        
        # Classificar items em batches com processamento paralelo
        console.print("[bold magenta]Iniciando classificação em batches com processamento paralelo...[/bold magenta]")
        results = classify_items_batched(
            df_items, 
            catmat_embeddings, 
            catmat_meta, 
            catser_embeddings, 
            catser_meta,
            existing_results,
            last_processed
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        console.print(f"[green]Classificação de todos os itens concluída em {total_time/60:.2f} minutos![/green]")
        console.print(f"[green]({total_time:.2f} segundos total, {total_time/len(df_items):.4f} segundos por item)[/green]")
        console.print(f"[cyan]Os embeddings foram salvos em:")
        console.print(f"- Catálogos: {EMBEDDING_PATH}")
        console.print(f"- Itens: {ITEMS_EMBED_PATH}[/cyan]")
        console.print(f"[bold blue]Modelo de embeddings utilizado: {MODEL_NAME} via API HTTP")
        
    except Exception as e:
        console.print(f"[bold red]Pipeline falhou: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

# Executar o código principal
if __name__ == "__main__":
    main()