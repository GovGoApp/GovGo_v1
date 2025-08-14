### EMB_NV2_v3 (EMBEDDING NIVEL 2 V3) ###

# Este script é responsável por gerar embeddings para itens de compras e classificá-los em categorias de materiais e serviços.
# Modificação: Adicionada a funcionalidade de checkpoint para salvar o progresso e permitir a recuperação em caso de falha.

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from openai import OpenAI
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn, TaskProgressColumn
from concurrent.futures import ThreadPoolExecutor
import threading
import pickle
import time

# Criar uma instância de console para exibição formatada
console = Console()

# Configuração da OpenAI
client = OpenAI(api_key="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")

# Definir caminhos e arquivos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = BASE_PATH + "CAT\\"
REPORTS_PATH = BASE_PATH + "REPORTS\\"
EXCEL_FILE = REPORTS_PATH + "CONTRATACAO_ID_ITENS_TOTAL.xlsx"
CATMAT_FILE = CAT_PATH + "CATMAT_nv2.json"
CATSER_FILE = CAT_PATH + "CATSER_nv2.json"
SHEET = "OBJETOS"

# Caminhos para armazenamento de embeddings
EMBEDDINGS_DIR = CAT_PATH + "EMBEDDINGS\\"
CATMAT_EMBED_FILE = EMBEDDINGS_DIR + "catmat_embeddings.pkl"
CATSER_EMBED_FILE = EMBEDDINGS_DIR + "catser_embeddings.pkl"
ITEMS_EMBED_DIR = EMBEDDINGS_DIR + "items\\"

# Modelo de embedding
EMBEDDING_MODEL= "text-embedding-ada-002"
#EMBEDDING_MODEL = "text-embedding-3-small"
#EMBEDDING_MODEL = "text-embedding-3-large"

# Criar diretórios se não existirem
for directory in [EMBEDDINGS_DIR, ITEMS_EMBED_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Nome do arquivo de saída com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
#OUTPUT_FILE = REPORTS_PATH + f"CLASSIFICACAO_EMB_TOTAL_{TIMESTAMP}.xlsx"
OUTPUT_FILE = REPORTS_PATH + "CLASSIFICACAO_EMB_TOTAL_v3_parte1.xlsx"
CHECKPOINT_FILE = REPORTS_PATH + f"CHECKPOINT_EMB_V32_{TIMESTAMP}.pkl"
#CHECKPOINT_FILE = REPORTS_PATH + "CHECKPOINT_EMB_20250403_1809.pkl"
BATCH_SIZE = 10000  # Tamanho do batch para processamento e salvamento

# Constantes para controle de execução
MAX_WORKERS = min(32, os.cpu_count() * 4) # Número de threads para processamento paralelo
console.print("WORKERS = " + str(MAX_WORKERS))

# Criar lock para acessos concorrentes
results_lock = threading.Lock()
checkpoint_lock = threading.Lock()
embedding_lock = threading.Lock() 

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
    """Carregar dados do Excel e arquivos de catálogo com recuperação inteligente baseada no último ID."""
    console.print("[bold magenta]Carregando dados...[/bold magenta]")
    
    # Verificar se existe um checkpoint para continuar o processamento
    checkpoint = load_checkpoint()
    existing_results = pd.DataFrame()
    
    # Verificar se OUTPUT_FILE existe e usá-lo para recuperação 
    if os.path.exists(OUTPUT_FILE):
        try:
            existing_results = pd.read_excel(OUTPUT_FILE)
            console.print(f"[green]Carregados {len(existing_results)} resultados do arquivo existente: {OUTPUT_FILE}[/green]")
            
            # Encontrar o último ID processado
            if len(existing_results) > 0:
                console.print("[cyan]Determinando ponto de continuação baseado no último ID processado...[/cyan]")
                
                # Obter o último ID do arquivo de resultados - CORRIGIDO para usar id_pncp
                last_id = existing_results.iloc[-1].get("id_pncp")
                console.print(f"[cyan]Último ID processado: {last_id}[/cyan]")
                
                # Carregar apenas os IDs do arquivo de entrada para encontrar onde continuar
                # CORRIGIDO para usar apenas id_pncp
                df_ids_only = pd.read_excel(EXCEL_FILE, sheet_name=SHEET, usecols=["id_pncp"])
                
                # Procurar pelo último ID processado
                found_idx = -1
                for i, row in df_ids_only.iterrows():
                    if str(row.get("id_pncp")) == str(last_id):
                        found_idx = i
                        break  # Adicionado break para parar assim que encontrar
                
                if found_idx >= 0:
                    # Continuamos a partir da linha seguinte ao ID encontrado
                    last_processed = found_idx + 1
                    console.print(f"[green]ID {last_id} encontrado na linha {found_idx+1}. Continuando da linha {last_processed+1}.[/green]")
                    
                    # Carregar apenas as linhas ainda não processadas
                    skiprows = list(range(1, last_processed + 1))  # Pular cabeçalho + linhas já processadas
                    df_items = pd.read_excel(EXCEL_FILE, sheet_name=SHEET, skiprows=skiprows)
                    console.print(f"[green]Carregados {len(df_items)} itens restantes do Excel para processamento.[/green]")
                    
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
                    
                    return df_items, catmat, catser, existing_results, {"last_processed": last_processed}
                else:
                    console.print("[yellow]ID final não encontrado no arquivo de entrada. Começando do início...[/yellow]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar resultados anteriores: {str(e)}[/bold red]")
    
    # Se não encontramos o ID ou o arquivo não existe, começamos do início
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
    
    return df_items, catmat, catser, existing_results, {"last_processed": 0}


def save_checkpoint(last_processed, output_file):
    """Salvar checkpoint para continuar processamento posteriormente."""
    with checkpoint_lock:
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'last_processed': last_processed,
            'output_file': output_file
        }
        
        with open(CHECKPOINT_FILE, 'wb') as f:
            pickle.dump(checkpoint, f)

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

def get_embeddings(texts, model = EMBEDDING_MODEL, batch_size=100, show_progress=True):
    """Gerar embeddings para uma lista de textos usando a API da OpenAI."""
    embeddings = []
    
    # Processar em lotes para evitar limites de token ou requisição
    total_batches = int(np.ceil(len(texts) / batch_size))
    
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
                batch_embeddings = process_batch(batch, model)
                embeddings.extend(batch_embeddings)
                progress.update(task, advance=1)
    else:
        # Loop de processamento sem progresso visível
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = process_batch(batch, model)
            embeddings.extend(batch_embeddings)
    
    return embeddings

def process_batch(batch, model):
    """Processa um lote de textos para embeddings, com tentativas em caso de erro."""
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=model, 
                input=batch
            )
            return [np.array(item.embedding, dtype=float) for item in response.data]
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                retry_delay += attempt * 2  # Backoff exponencial
                console.print(f"[yellow]Limite de taxa atingido. Tentativa {attempt+1}/{max_retries}. Aguardando {retry_delay} segundos...[/yellow]")
                time.sleep(retry_delay)
            else:
                if attempt == max_retries - 1:
                    console.print(f"[bold red]Erro após {max_retries} tentativas: {str(e)}[/bold red]")
                else:
                    console.print(f"[bold red]Erro na API OpenAI: {str(e)}[/bold red]")
                raise

def process_item(args):
    """Função para processar um único item (para uso com ThreadPoolExecutor)."""
    idx, item_id, description, catmat_matrix, catser_matrix, catmat_meta, catser_meta, top_n = args
    
    try:
        # Verificar se a descrição é válida
        if not description or pd.isna(description) or description.lower() in ["nan", "none"]:
            return idx, item_id, {
                "id": item_id,
                "objetoCompra": description,
                "tipoDetectado": "Não classificado",
                "categoriaMelhor": "Descrição inválida",
                "scoreCategoria": 0.0,
                "categoriasTopN": []
            }
        
        # Obter embedding para a descrição do item
        item_emb = get_embeddings([description], show_progress=False)[0]
        
        # Calcular similaridade com CATMAT e CATSER
        catmat_scores = catmat_matrix.dot(item_emb)
        catser_scores = catser_matrix.dot(item_emb)
        
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
            "id_pncp": item_id,
            "objetoCompra": description,
            "tipoDetectado": tipo,
            "categoriaMelhor": best_category_str,
            "scoreCategoria": float(best_mat_score if tipo == "Material" else best_ser_score),
            "categoriasTopN": top_list_str
        }
    except Exception as e:
        console.print(f"[bold red]Erro processando item {item_id}: {str(e)}[/bold red]")
        return idx, item_id, {
            "id": item_id,
            "objetoCompra": description,
            "tipoDetectado": "Erro",
            "categoriaMelhor": f"Erro: {str(e)}",
            "scoreCategoria": 0.0,
            "categoriasTopN": []
        }

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
        
        # 2. Obter embeddings para todo o batch de uma vez (operação de API)
        console.print("[bold cyan]Obtendo embeddings para todo o batch...[/bold cyan]")
        
        try:
            # Obter embeddings apenas para descrições não vazias
            valid_indices = [i for i, desc in enumerate(descriptions) if desc]
            valid_descriptions = [descriptions[i] for i in valid_indices]
            
            if valid_descriptions:
                # Obter embeddings em lotes de 100 (limite da API)
                item_embeddings = get_embeddings(valid_descriptions, show_progress=True)
                
                # Mapear de volta para o índice original
                all_item_embeddings = [None] * len(descriptions)
                for i, emb in zip(valid_indices, item_embeddings):
                    all_item_embeddings[i] = emb
                
                # NOVO: Salvar embeddings dos itens em arquivo pickle
                try:
                    # Criar dicionário com ID como chave e embedding como valor
                    item_embeddings_dict = {}
                    for i, emb in zip(valid_indices, item_embeddings):
                        if item_ids[i]:  # Verificar se o ID é válido
                            item_embeddings_dict[str(item_ids[i])] = emb.tolist()
                    
                    # Nome do arquivo incluindo range de batch e timestamp
                    batch_embed_file = f"{ITEMS_EMBED_DIR}items_batch_{batch_start}_{batch_end}_{TIMESTAMP}.pkl"
                    save_embeddings(item_embeddings_dict, batch_embed_file)
                    console.print(f"[green]Embeddings de {len(item_embeddings_dict)} itens salvos em {batch_embed_file}[/green]")
                except Exception as e:
                    console.print(f"[bold red]Erro ao salvar embeddings dos itens: {str(e)}[/bold red]")
            else:
                all_item_embeddings = []
                
        except Exception as e:
            console.print(f"[bold red]Erro ao obter embeddings do batch: {str(e)}[/bold red]")
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
        
        # Usar ThreadPoolExecutor para classificação paralela (puramente local, sem API)
        batch_results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Classificando items..."),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn()
        ) as progress:
            task_items = progress.add_task("", total=len(classification_args))
            
            # Usar workers para cálculos locais
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
        
        # Processar as categorias top N antes de salvar (converter lista para string)
        if 'categoriasTopN' in df_batch_results.columns:
            df_batch_results['categoriasTopN'] = df_batch_results['categoriasTopN'].apply(
                lambda x: '\n'.join(x) if isinstance(x, list) else str(x))
        
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
        cols.insert(cols.index("categoriasTopN"), "scoreCategoria")
        all_results = all_results[cols]
    
    # Salvar versão final
    try:
        all_results.to_excel(OUTPUT_FILE, index=False)
        console.print(f"[bold green]Resultados finais salvos em: {OUTPUT_FILE}[/bold green]")
        
        # Remover arquivo incremental e checkpoint após sucesso
        if os.path.exists(temp_output):
            os.remove(temp_output)
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
    except Exception as e:
        console.print(f"[bold red]Erro ao salvar resultados finais: {str(e)}[/bold red]")
    
    return all_results


def classify_item_local(args):
    """Função para classificação local sem chamadas à API."""
    idx, item_id, description, item_emb, catmat_matrix, catser_matrix, catmat_meta, catser_meta, top_n = args
    
    # Se não temos embedding, é um item inválido
    if item_emb is None:
        return idx, item_id, {
            "id_pncp": item_id,
            "objetoCompra": description,
            "tipoDetectado": "Não classificado",
            "categoriaMelhor": "Descrição inválida",
            "scoreCategoria": 0.0,
            "categoriasTopN": []
        }
    
    try:
        # Calcular similaridade com CATMAT e CATSER (operação puramente local e rápida)
        catmat_scores = catmat_matrix.dot(item_emb)
        catser_scores = catser_matrix.dot(item_emb)
        
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
            "id_pncp": item_id,
            "objetoCompra": description,
            "tipoDetectado": tipo,
            "categoriaMelhor": best_category_str,
            "scoreCategoria": float(best_mat_score if tipo == "Material" else best_ser_score),
            "categoriasTopN": top_list_str
        }
    except Exception as e:
        console.print(f"[bold red]Erro na classificação do item {item_id}: {str(e)}[/bold red]")
        return idx, item_id, {
            "id": item_id,
            "objetoCompra": description,
            "tipoDetectado": "Erro",
            "categoriaMelhor": f"Erro: {str(e)}",
            "scoreCategoria": 0.0,
            "categoriasTopN": []
        }

def main():
    start_time = time.time()
    
    try:
        # Carregar dados e verificar se existe checkpoint
        df_items, catmat, catser, existing_results, checkpoint_info = load_data()
        last_processed = checkpoint_info.get('last_processed', 0)
        
        # Preparar textos de catálogo para embeddings
        catmat_texts, catmat_meta, catser_texts, catser_meta = prepare_catalog_entries(catmat, catser)
        
        # Verificar se há embeddings de catálogo pré-existentes
        console.print("[bold magenta]Verificando embeddings de catálogo existentes...[/bold magenta]")
        
        catmat_embeddings = load_embeddings(CATMAT_EMBED_FILE)
        if catmat_embeddings is None or len(catmat_embeddings) != len(catmat_texts):
            console.print("[yellow]Embeddings de CATMAT não encontrados ou desatualizados. Gerando novos...[/yellow]")
            catmat_embeddings = get_embeddings(catmat_texts)
            save_embeddings(catmat_embeddings, CATMAT_EMBED_FILE)
        
        catser_embeddings = load_embeddings(CATSER_EMBED_FILE)
        if catser_embeddings is None or len(catser_embeddings) != len(catser_texts):
            console.print("[yellow]Embeddings de CATSER não encontrados ou desatualizados. Gerando novos...[/yellow]")
            catser_embeddings = get_embeddings(catser_texts)
            save_embeddings(catser_embeddings, CATSER_EMBED_FILE)
        
        console.print("[green]Embeddings de categorias preparados.[/green]")
        
        # Classificar items em batches com processamento paralelo
        console.print("[bold magenta]Iniciando classificação em batches com processamento paralelo...[/bold magenta]")
        console.print(f"[cyan]Continuando a partir da linha {last_processed+1} do arquivo de entrada[/cyan]")
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
        console.print(f"- Catálogos: {EMBEDDINGS_DIR}")
        console.print(f"- Itens: {ITEMS_EMBED_DIR}[/cyan]")
        
    except Exception as e:
        console.print(f"[bold red]Pipeline falhou: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())


# Executar o código principal
if __name__ == "__main__":
    main()